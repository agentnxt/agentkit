"""AgentCrew SDK — programmatic interface for building agent crews."""

from dataclasses import dataclass, field
from typing import Callable, Optional
import httpx


@dataclass
class Agent:
    name: str
    role: str
    goal: str
    backstory: str = ""
    model: str = "ollama/qwen3:30b-a3b"
    tools: list[Callable] = field(default_factory=list)


@dataclass
class Task:
    description: str
    agent: Agent
    expected_output: str = ""
    context: list["Task"] = field(default_factory=list)


@dataclass
class Crew:
    agents: list[Agent]
    tasks: list[Task]
    verbose: bool = False

    async def kickoff(self, inputs: dict = None) -> dict:
        results = []
        for task in self.tasks:
            if self.verbose:
                print(f"[{task.agent.name}] {task.description}")
            result = await self._execute_task(task, inputs or {}, results)
            results.append({"task": task.description, "result": result})
        return {"results": results}

    async def _execute_task(self, task: Task, inputs: dict, prior: list) -> str:
        context = "\n".join(r["result"] for r in prior) if prior else ""
        prompt = f"""Role: {task.agent.role}
Goal: {task.agent.goal}
Task: {task.description}
Context: {context}
Inputs: {inputs}"""

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self._llm_url}/chat/completions",
                json={
                    "model": task.agent.model,
                    "messages": [
                        {"role": "system", "content": task.agent.backstory},
                        {"role": "user", "content": prompt},
                    ],
                },
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            return f"Error: {r.status_code}"

    @property
    def _llm_url(self):
        import os
        return os.environ.get("LITELLM_URL", "https://llm.openautonomyx.com")

    @property
    def _api_key(self):
        import os
        return os.environ.get("LITELLM_API_KEY", "")


class AgentCrew:
    """High-level factory for building crews."""

    @staticmethod
    def create(agents: list[Agent], tasks: list[Task], verbose: bool = False) -> Crew:
        return Crew(agents=agents, tasks=tasks, verbose=verbose)
