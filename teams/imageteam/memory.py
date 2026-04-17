"""
Image Agent Memory — remembers past generations, preferences, conversations.

Storage:
  - Qdrant: vector embeddings of past images + prompts for similarity search
  - SurrealDB: conversation history, user preferences, session state

Compaction:
  - Summarizes long conversations to fit context window
  - Keeps key decisions and preferences, drops verbose tool outputs
"""

import os
import json
import httpx
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional


QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
SURREAL_URL = os.environ.get("SURREAL_URL", "")
SURREAL_NS = os.environ.get("SURREAL_NS", "autonomyx")
SURREAL_DB = os.environ.get("SURREAL_DB", "agents")
SURREAL_USER = os.environ.get("SURREAL_USER", "")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
COLLECTION = "image_agent_memory"


@dataclass
class MemoryEntry:
    id: str
    prompt: str
    tool_used: str
    result_summary: str
    user_id: str = ""
    session_id: str = ""
    timestamp: str = ""
    preferences: dict = field(default_factory=dict)
    image_url: str = ""
    feedback: str = ""


class VectorMemory:
    """Qdrant-backed vector memory for semantic search over past generations."""

    async def _embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{OLLAMA_URL}/api/embed", json={
                "model": "nomic-embed-text",
                "input": text[:2000],
            })
            if r.status_code == 200:
                return r.json()["embeddings"][0]
        return []

    async def _ensure_collection(self):
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{QDRANT_URL}/collections/{COLLECTION}")
            if r.status_code == 404:
                await client.put(f"{QDRANT_URL}/collections/{COLLECTION}", json={
                    "vectors": {"size": 768, "distance": "Cosine"},
                })

    async def store(self, entry: MemoryEntry):
        await self._ensure_collection()
        embedding = await self._embed(f"{entry.prompt} {entry.result_summary}")
        if not embedding:
            return

        point_id = str(uuid.uuid4())
        async with httpx.AsyncClient(timeout=10) as client:
            await client.put(f"{QDRANT_URL}/collections/{COLLECTION}/points", json={
                "points": [{
                    "id": point_id,
                    "vector": embedding,
                    "payload": {
                        "prompt": entry.prompt,
                        "tool_used": entry.tool_used,
                        "result_summary": entry.result_summary,
                        "user_id": entry.user_id,
                        "session_id": entry.session_id,
                        "timestamp": entry.timestamp or datetime.now(timezone.utc).isoformat(),
                        "image_url": entry.image_url,
                        "feedback": entry.feedback,
                        "preferences": entry.preferences,
                    },
                }],
            })

    async def search(self, query: str, user_id: str = "", limit: int = 5) -> list[dict]:
        embedding = await self._embed(query)
        if not embedding:
            return []

        filter_cond = None
        if user_id:
            filter_cond = {"must": [{"key": "user_id", "match": {"value": user_id}}]}

        async with httpx.AsyncClient(timeout=10) as client:
            payload = {"vector": embedding, "limit": limit, "with_payload": True}
            if filter_cond:
                payload["filter"] = filter_cond
            r = await client.post(
                f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
                json=payload,
            )
            if r.status_code == 200:
                return [
                    {**hit["payload"], "score": hit["score"]}
                    for hit in r.json().get("result", [])
                ]
        return []


class SessionMemory:
    """SurrealDB-backed session memory for conversation history and preferences."""

    async def _query(self, query: str, vars: dict = None):
        if not SURREAL_URL:
            return None
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{SURREAL_URL}/rpc",
                headers={
                    "surreal-ns": SURREAL_NS,
                    "surreal-db": SURREAL_DB,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                auth=(SURREAL_USER, SURREAL_PASS),
                json={"id": 1, "method": "query", "params": [query, vars or {}]},
            )
            return r.json().get("result", [])

    async def save_turn(self, session_id: str, user_id: str, role: str, content: str):
        await self._query(
            """CREATE image_session SET
                session_id = $session_id,
                user_id = $user_id,
                role = $role,
                content = $content,
                timestamp = time::now();""",
            {"session_id": session_id, "user_id": user_id, "role": role, "content": content},
        )

    async def get_history(self, session_id: str, limit: int = 50) -> list[dict]:
        result = await self._query(
            "SELECT * FROM image_session WHERE session_id = $sid ORDER BY timestamp ASC LIMIT $limit;",
            {"sid": session_id, "limit": limit},
        )
        if result and result[0].get("result"):
            return [{"role": r["role"], "content": r["content"]} for r in result[0]["result"]]
        return []

    async def save_preference(self, user_id: str, key: str, value: str):
        await self._query(
            """UPSERT image_preference SET
                user_id = $uid,
                pref_key = $key,
                pref_value = $value,
                updated_at = time::now()
            WHERE user_id = $uid AND pref_key = $key;""",
            {"uid": user_id, "key": key, "value": value},
        )

    async def get_preferences(self, user_id: str) -> dict:
        result = await self._query(
            "SELECT pref_key, pref_value FROM image_preference WHERE user_id = $uid;",
            {"uid": user_id},
        )
        if result and result[0].get("result"):
            return {r["pref_key"]: r["pref_value"] for r in result[0]["result"]}
        return {}


class ConversationCompactor:
    """Compacts long conversations to fit context window."""

    def __init__(self, max_turns: int = 20, summary_threshold: int = 30):
        self.max_turns = max_turns
        self.summary_threshold = summary_threshold

    async def compact(self, history: list[dict]) -> list[dict]:
        if len(history) <= self.max_turns:
            return history

        old = history[: -self.max_turns]
        recent = history[-self.max_turns:]

        summary = await self._summarize(old)
        return [{"role": "system", "content": f"Previous conversation summary:\n{summary}"}] + recent

    async def _summarize(self, turns: list[dict]) -> str:
        conversation = "\n".join(f"{t['role']}: {t['content'][:200]}" for t in turns)

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json={
                "model": "qwen2.5:7b",
                "prompt": f"""Summarize this conversation concisely. Keep:
- User's style preferences (colors, themes, styles)
- Key decisions made
- Images generated and feedback given
- Any recurring requests

Conversation:
{conversation[:4000]}""",
                "stream": False,
            })
            if r.status_code == 200:
                return r.json().get("response", "")

        return f"[{len(turns)} previous turns — preferences and context carried forward]"


class ImageMemory:
    """Combined memory — vector search + session history + compaction."""

    def __init__(self, user_id: str = "", session_id: str = ""):
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.vector = VectorMemory()
        self.session = SessionMemory()
        self.compactor = ConversationCompactor()

    async def remember(self, prompt: str, tool: str, result: str, image_url: str = ""):
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            prompt=prompt,
            tool_used=tool,
            result_summary=result[:500],
            user_id=self.user_id,
            session_id=self.session_id,
            image_url=image_url,
        )
        await self.vector.store(entry)
        await self.session.save_turn(self.session_id, self.user_id, "assistant", f"[{tool}] {result[:200]}")

    async def recall(self, query: str, limit: int = 5) -> list[dict]:
        return await self.vector.search(query, user_id=self.user_id, limit=limit)

    async def get_context(self) -> list[dict]:
        history = await self.session.get_history(self.session_id)
        return await self.compactor.compact(history)

    async def save_input(self, prompt: str):
        await self.session.save_turn(self.session_id, self.user_id, "user", prompt)

    async def set_preference(self, key: str, value: str):
        await self.session.save_preference(self.user_id, key, value)

    async def get_preferences(self) -> dict:
        return await self.session.get_preferences(self.user_id)
