"""
Publishing and scheduling tools — post to social media, schedule content calendar.
"""

import os
import httpx
from datetime import datetime
from typing import Optional


BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN", "")
POSTIZ_URL = os.environ.get("POSTIZ_URL", "")
POSTIZ_KEY = os.environ.get("POSTIZ_API_KEY", "")
TYPEFULLY_TOKEN = os.environ.get("TYPEFULLY_API_KEY", "")
WORDPRESS_URL = os.environ.get("WORDPRESS_URL", "")
WORDPRESS_USER = os.environ.get("WORDPRESS_USER", "")
WORDPRESS_APP_PASS = os.environ.get("WORDPRESS_APP_PASSWORD", "")
CALCOM_URL = os.environ.get("CALCOM_URL", "")
CALCOM_KEY = os.environ.get("CALCOM_API_KEY", "")
NOCODB_URL = os.environ.get("NOCODB_URL", "")
NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "")


# ── Multi-platform Publishing (Postiz — open source) ────────────────────

async def postiz_schedule(
    content: str,
    platforms: list[str],
    image_url: str = "",
    scheduled_at: str = "",
) -> dict:
    """Schedule a post to multiple platforms via Postiz (open-source social scheduler)."""
    if not POSTIZ_URL:
        return {"error": "POSTIZ_URL not configured"}
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "content": content,
            "platforms": platforms,
        }
        if image_url:
            payload["media"] = [{"url": image_url, "type": "image"}]
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at
        r = await client.post(
            f"{POSTIZ_URL}/api/posts",
            headers={"Authorization": f"Bearer {POSTIZ_KEY}"},
            json=payload,
        )
        if r.status_code in (200, 201):
            return {"post": r.json(), "tool": "postiz", "action": "schedule"}
        return {"error": r.text}


async def postiz_list_scheduled() -> dict:
    """List all scheduled posts."""
    if not POSTIZ_URL:
        return {"error": "POSTIZ_URL not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{POSTIZ_URL}/api/posts?status=scheduled",
            headers={"Authorization": f"Bearer {POSTIZ_KEY}"},
        )
        if r.status_code == 200:
            return {"posts": r.json(), "tool": "postiz"}
        return {"error": r.text}


# ── Buffer (social scheduling) ──────────────────────────────────────────

async def buffer_schedule(
    text: str,
    profile_ids: list[str],
    image_url: str = "",
    scheduled_at: str = "",
) -> dict:
    """Schedule a post via Buffer."""
    if not BUFFER_TOKEN:
        return {"error": "BUFFER_ACCESS_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "text": text,
            "profile_ids": profile_ids,
        }
        if image_url:
            payload["media"] = {"photo": image_url}
        if scheduled_at:
            payload["scheduled_at"] = scheduled_at
        else:
            payload["now"] = True
        r = await client.post(
            "https://api.bufferapp.com/1/updates/create.json",
            headers={"Authorization": f"Bearer {BUFFER_TOKEN}"},
            data=payload,
        )
        if r.status_code in (200, 201):
            return {"update": r.json(), "tool": "buffer", "action": "schedule"}
        return {"error": r.text}


# ── Typefully (Twitter/X threads) ───────────────────────────────────────

async def typefully_draft(
    content: str,
    schedule: bool = False,
    scheduled_date: str = "",
) -> dict:
    """Create a Twitter/X draft or schedule via Typefully."""
    if not TYPEFULLY_TOKEN:
        return {"error": "TYPEFULLY_API_KEY not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        payload = {"content": content}
        if schedule and scheduled_date:
            payload["schedule-date"] = scheduled_date
        r = await client.post(
            "https://api.typefully.com/v1/drafts/",
            headers={"X-API-KEY": TYPEFULLY_TOKEN},
            json=payload,
        )
        if r.status_code in (200, 201):
            return {"draft": r.json(), "tool": "typefully", "action": "draft"}
        return {"error": r.text}


# ── WordPress Publishing ────────────────────────────────────────────────

async def wordpress_publish(
    title: str,
    content: str,
    status: str = "draft",
    featured_image_url: str = "",
    categories: list[str] = None,
    tags: list[str] = None,
    scheduled_date: str = "",
) -> dict:
    """Create/schedule a WordPress post."""
    if not WORDPRESS_URL:
        return {"error": "WORDPRESS_URL not configured"}
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "title": title,
            "content": content,
            "status": status if not scheduled_date else "future",
        }
        if scheduled_date:
            payload["date"] = scheduled_date
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags

        auth = (WORDPRESS_USER, WORDPRESS_APP_PASS) if WORDPRESS_USER else None
        r = await client.post(
            f"{WORDPRESS_URL}/wp-json/wp/v2/posts",
            auth=auth,
            json=payload,
        )
        if r.status_code in (200, 201):
            post = r.json()
            return {"post_id": post["id"], "link": post.get("link", ""), "tool": "wordpress", "action": "publish"}
        return {"error": r.text}


# ── Content Calendar (NocoDB or SurrealDB) ───────────────────────────────

async def calendar_add_entry(
    title: str,
    platform: str,
    scheduled_date: str,
    content: str = "",
    image_url: str = "",
    status: str = "scheduled",
) -> dict:
    """Add entry to content calendar."""
    if NOCODB_URL and NOCODB_TOKEN:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{NOCODB_URL}/api/v1/db/data/noco/content_calendar",
                headers={"xc-auth": NOCODB_TOKEN},
                json={
                    "Title": title,
                    "Platform": platform,
                    "Scheduled Date": scheduled_date,
                    "Content": content,
                    "Image URL": image_url,
                    "Status": status,
                },
            )
            if r.status_code in (200, 201):
                return {"entry": r.json(), "tool": "nocodb_calendar"}
            return {"error": r.text}

    return {
        "entry": {
            "title": title,
            "platform": platform,
            "scheduled_date": scheduled_date,
            "status": status,
        },
        "tool": "local_calendar",
        "note": "Stored locally — configure NOCODB_URL for persistent calendar",
    }


async def calendar_list(start_date: str = "", end_date: str = "") -> dict:
    """List content calendar entries."""
    if NOCODB_URL and NOCODB_TOKEN:
        async with httpx.AsyncClient(timeout=15) as client:
            params = {}
            if start_date:
                params["where"] = f"(Scheduled Date,gte,{start_date})"
            r = await client.get(
                f"{NOCODB_URL}/api/v1/db/data/noco/content_calendar",
                headers={"xc-auth": NOCODB_TOKEN},
                params=params,
            )
            if r.status_code == 200:
                return {"entries": r.json().get("list", []), "tool": "nocodb_calendar"}
            return {"error": r.text}

    return {"entries": [], "tool": "local_calendar", "note": "Configure NOCODB_URL"}


# ── Cal.com (scheduling meetings about content) ─────────────────────────

async def calcom_create_booking(
    event_type_id: int,
    start: str,
    name: str,
    email: str,
    notes: str = "",
) -> dict:
    """Create a Cal.com booking (e.g., content review meeting)."""
    if not CALCOM_URL:
        return {"error": "CALCOM_URL not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{CALCOM_URL}/v1/bookings",
            params={"apiKey": CALCOM_KEY},
            json={
                "eventTypeId": event_type_id,
                "start": start,
                "responses": {"name": name, "email": email},
                "metadata": {"notes": notes},
            },
        )
        if r.status_code in (200, 201):
            return {"booking": r.json(), "tool": "calcom"}
        return {"error": r.text}


PUBLISH_TOOL_MAP = {
    "postiz_schedule": postiz_schedule,
    "postiz_list": postiz_list_scheduled,
    "buffer_schedule": buffer_schedule,
    "typefully_draft": typefully_draft,
    "wordpress_publish": wordpress_publish,
    "calendar_add": calendar_add_entry,
    "calendar_list": calendar_list,
    "calcom_booking": calcom_create_booking,
}
