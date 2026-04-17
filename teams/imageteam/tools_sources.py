"""
Image source integrations — search and fetch from stock/free image platforms.
"""

import os
import httpx
from typing import Optional


UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
FLICKR_KEY = os.environ.get("FLICKR_API_KEY", "")
GOOGLE_PHOTOS_TOKEN = os.environ.get("GOOGLE_PHOTOS_TOKEN", "")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")


# ── Unsplash ─────────────────────────────────────────────────────────────

async def unsplash_search(query: str, count: int = 10, orientation: str = "") -> dict:
    """Search Unsplash for free images."""
    if not UNSPLASH_KEY:
        return {"error": "UNSPLASH_ACCESS_KEY not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        params = {"query": query, "per_page": count}
        if orientation:
            params["orientation"] = orientation
        r = await client.get(
            "https://api.unsplash.com/search/photos",
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            params=params,
        )
        if r.status_code == 200:
            results = r.json().get("results", [])
            return {
                "images": [
                    {
                        "id": img["id"],
                        "url": img["urls"]["regular"],
                        "thumb": img["urls"]["thumb"],
                        "full": img["urls"]["full"],
                        "description": img.get("description") or img.get("alt_description", ""),
                        "author": img["user"]["name"],
                        "download_url": img["links"]["download"],
                        "license": "Unsplash License (free)",
                    }
                    for img in results
                ],
                "total": r.json().get("total", 0),
                "tool": "unsplash",
            }
        return {"error": r.text}


async def unsplash_random(count: int = 1, query: str = "") -> dict:
    """Get random photos from Unsplash."""
    if not UNSPLASH_KEY:
        return {"error": "UNSPLASH_ACCESS_KEY not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        params = {"count": count}
        if query:
            params["query"] = query
        r = await client.get(
            "https://api.unsplash.com/photos/random",
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            params=params,
        )
        if r.status_code == 200:
            photos = r.json() if isinstance(r.json(), list) else [r.json()]
            return {
                "images": [{"url": p["urls"]["regular"], "description": p.get("description", "")} for p in photos],
                "tool": "unsplash",
            }
        return {"error": r.text}


# ── Flickr ───────────────────────────────────────────────────────────────

async def flickr_search(query: str, count: int = 10, license: str = "4,5,6,9,10") -> dict:
    """Search Flickr for Creative Commons images."""
    if not FLICKR_KEY:
        return {"error": "FLICKR_API_KEY not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://www.flickr.com/services/rest/",
            params={
                "method": "flickr.photos.search",
                "api_key": FLICKR_KEY,
                "text": query,
                "per_page": count,
                "format": "json",
                "nojsoncallback": 1,
                "extras": "url_l,url_m,description,license,owner_name",
                "license": license,
                "sort": "relevance",
            },
        )
        if r.status_code == 200:
            photos = r.json().get("photos", {}).get("photo", [])
            return {
                "images": [
                    {
                        "id": p["id"],
                        "url": p.get("url_l") or p.get("url_m", ""),
                        "title": p.get("title", ""),
                        "author": p.get("ownername", ""),
                        "license": f"CC (license id: {p.get('license', '')})",
                    }
                    for p in photos if p.get("url_l") or p.get("url_m")
                ],
                "tool": "flickr",
            }
        return {"error": r.text}


# ── Openverse (Creative Commons) ────────────────────────────────────────

async def openverse_search(query: str, count: int = 10, license_type: str = "") -> dict:
    """Search Openverse for openly licensed images."""
    async with httpx.AsyncClient(timeout=15) as client:
        params = {"q": query, "page_size": count}
        if license_type:
            params["license_type"] = license_type
        r = await client.get("https://api.openverse.org/v1/images/", params=params)
        if r.status_code == 200:
            results = r.json().get("results", [])
            return {
                "images": [
                    {
                        "id": img["id"],
                        "url": img.get("url", ""),
                        "thumb": img.get("thumbnail", ""),
                        "title": img.get("title", ""),
                        "author": img.get("creator", ""),
                        "license": img.get("license", ""),
                        "license_url": img.get("license_url", ""),
                        "source": img.get("source", ""),
                    }
                    for img in results
                ],
                "total": r.json().get("result_count", 0),
                "tool": "openverse",
            }
        return {"error": r.text}


# ── Pexels (bonus — free stock) ──────────────────────────────────────────

async def pexels_search(query: str, count: int = 10, orientation: str = "") -> dict:
    """Search Pexels for free stock images."""
    if not PEXELS_KEY:
        return {"error": "PEXELS_API_KEY not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        params = {"query": query, "per_page": count}
        if orientation:
            params["orientation"] = orientation
        r = await client.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params=params,
        )
        if r.status_code == 200:
            photos = r.json().get("photos", [])
            return {
                "images": [
                    {
                        "id": p["id"],
                        "url": p["src"]["large"],
                        "thumb": p["src"]["medium"],
                        "original": p["src"]["original"],
                        "photographer": p.get("photographer", ""),
                        "license": "Pexels License (free)",
                    }
                    for p in photos
                ],
                "tool": "pexels",
            }
        return {"error": r.text}


# ── Google Photos ────────────────────────────────────────────────────────

async def google_photos_search(query: str, count: int = 10) -> dict:
    """Search Google Photos library."""
    if not GOOGLE_PHOTOS_TOKEN:
        return {"error": "GOOGLE_PHOTOS_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:search",
            headers={"Authorization": f"Bearer {GOOGLE_PHOTOS_TOKEN}"},
            json={
                "pageSize": count,
                "filters": {"contentFilter": {"includedContentCategories": []}, "mediaTypeFilter": {"mediaTypes": ["PHOTO"]}},
            },
        )
        if r.status_code == 200:
            items = r.json().get("mediaItems", [])
            return {
                "images": [
                    {
                        "id": item["id"],
                        "url": item.get("baseUrl", ""),
                        "filename": item.get("filename", ""),
                        "description": item.get("description", ""),
                        "created": item.get("mediaMetadata", {}).get("creationTime", ""),
                    }
                    for item in items
                ],
                "tool": "google_photos",
            }
        return {"error": r.text}


# ── Combined source tool map ────────────────────────────────────────────

SOURCE_TOOL_MAP = {
    "unsplash_search": unsplash_search,
    "unsplash_random": unsplash_random,
    "flickr_search": flickr_search,
    "openverse_search": openverse_search,
    "pexels_search": pexels_search,
    "google_photos_search": google_photos_search,
}
