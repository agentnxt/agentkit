"""
Design platform integrations — Canva, Figma, Adobe Creative Cloud.
Each tool wraps the platform's API.
"""

import os
import httpx
from typing import Optional


# ── Canva ────────────────────────────────────────────────────────────────

CANVA_TOKEN = os.environ.get("CANVA_API_TOKEN", "")
CANVA_API = "https://api.canva.com/rest/v1"


async def canva_create_design(
    title: str,
    design_type: str = "Presentation",
    width: int = 1920,
    height: int = 1080,
) -> dict:
    """Create a new Canva design."""
    if not CANVA_TOKEN:
        return {"error": "CANVA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{CANVA_API}/designs",
            headers={"Authorization": f"Bearer {CANVA_TOKEN}"},
            json={"title": title, "design_type": {"type": design_type}, "dimensions": {"width": width, "height": height}},
        )
        if r.status_code in (200, 201):
            return {"design": r.json(), "tool": "canva", "action": "create"}
        return {"error": r.text}


async def canva_upload_asset(image_url: str, name: str = "uploaded-image") -> dict:
    """Upload an image asset to Canva."""
    if not CANVA_TOKEN:
        return {"error": "CANVA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{CANVA_API}/asset-uploads",
            headers={"Authorization": f"Bearer {CANVA_TOKEN}"},
            json={"name": name, "url": image_url},
        )
        if r.status_code in (200, 201):
            return {"asset": r.json(), "tool": "canva", "action": "upload"}
        return {"error": r.text}


async def canva_export_design(design_id: str, format: str = "png") -> dict:
    """Export a Canva design to image."""
    if not CANVA_TOKEN:
        return {"error": "CANVA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{CANVA_API}/designs/{design_id}/exports",
            headers={"Authorization": f"Bearer {CANVA_TOKEN}"},
            json={"format": {"type": format}},
        )
        if r.status_code in (200, 201):
            return {"export": r.json(), "tool": "canva", "action": "export"}
        return {"error": r.text}


async def canva_list_designs(query: str = "", count: int = 20) -> dict:
    """List Canva designs."""
    if not CANVA_TOKEN:
        return {"error": "CANVA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        params = {"limit": count}
        if query:
            params["query"] = query
        r = await client.get(
            f"{CANVA_API}/designs",
            headers={"Authorization": f"Bearer {CANVA_TOKEN}"},
            params=params,
        )
        if r.status_code == 200:
            return {"designs": r.json(), "tool": "canva", "action": "list"}
        return {"error": r.text}


# ── Figma ────────────────────────────────────────────────────────────────

FIGMA_TOKEN = os.environ.get("FIGMA_API_TOKEN", "")
FIGMA_API = "https://api.figma.com/v1"


async def figma_get_file(file_key: str) -> dict:
    """Get a Figma file's structure."""
    if not FIGMA_TOKEN:
        return {"error": "FIGMA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{FIGMA_API}/files/{file_key}",
            headers={"X-Figma-Token": FIGMA_TOKEN},
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "name": data.get("name"),
                "pages": [{"name": p["name"], "id": p["id"]} for p in data.get("document", {}).get("children", [])],
                "tool": "figma",
                "action": "get_file",
            }
        return {"error": r.text}


async def figma_export_nodes(file_key: str, node_ids: list[str], format: str = "png", scale: float = 2.0) -> dict:
    """Export Figma nodes as images."""
    if not FIGMA_TOKEN:
        return {"error": "FIGMA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{FIGMA_API}/images/{file_key}",
            headers={"X-Figma-Token": FIGMA_TOKEN},
            params={"ids": ",".join(node_ids), "format": format, "scale": scale},
        )
        if r.status_code == 200:
            return {"images": r.json().get("images", {}), "tool": "figma", "action": "export"}
        return {"error": r.text}


async def figma_get_components(file_key: str) -> dict:
    """Get components from a Figma file."""
    if not FIGMA_TOKEN:
        return {"error": "FIGMA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{FIGMA_API}/files/{file_key}/components",
            headers={"X-Figma-Token": FIGMA_TOKEN},
        )
        if r.status_code == 200:
            return {"components": r.json().get("meta", {}).get("components", []), "tool": "figma", "action": "components"}
        return {"error": r.text}


async def figma_get_styles(file_key: str) -> dict:
    """Get styles (colors, text, effects) from a Figma file."""
    if not FIGMA_TOKEN:
        return {"error": "FIGMA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{FIGMA_API}/files/{file_key}/styles",
            headers={"X-Figma-Token": FIGMA_TOKEN},
        )
        if r.status_code == 200:
            return {"styles": r.json().get("meta", {}).get("styles", []), "tool": "figma", "action": "styles"}
        return {"error": r.text}


async def figma_post_comment(file_key: str, message: str, node_id: str = "") -> dict:
    """Post a comment on a Figma file."""
    if not FIGMA_TOKEN:
        return {"error": "FIGMA_API_TOKEN not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        payload = {"message": message}
        if node_id:
            payload["client_meta"] = {"node_id": node_id}
        r = await client.post(
            f"{FIGMA_API}/files/{file_key}/comments",
            headers={"X-Figma-Token": FIGMA_TOKEN, "Content-Type": "application/json"},
            json=payload,
        )
        if r.status_code in (200, 201):
            return {"comment": r.json(), "tool": "figma", "action": "comment"}
        return {"error": r.text}


# ── Adobe Creative Cloud ─────────────────────────────────────────────────

ADOBE_CLIENT_ID = os.environ.get("ADOBE_CLIENT_ID", "")
ADOBE_CLIENT_SECRET = os.environ.get("ADOBE_CLIENT_SECRET", "")
ADOBE_ACCESS_TOKEN = os.environ.get("ADOBE_ACCESS_TOKEN", "")
ADOBE_API = "https://image.adobe.io"


async def _adobe_token() -> str:
    """Get Adobe IMS access token."""
    if ADOBE_ACCESS_TOKEN:
        return ADOBE_ACCESS_TOKEN
    if not ADOBE_CLIENT_ID or not ADOBE_CLIENT_SECRET:
        return ""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://ims-na1.adobelogin.com/ims/token/v3",
            data={
                "grant_type": "client_credentials",
                "client_id": ADOBE_CLIENT_ID,
                "client_secret": ADOBE_CLIENT_SECRET,
                "scope": "openid,AdobeID,firefly_api,ff_apis",
            },
        )
        if r.status_code == 200:
            return r.json().get("access_token", "")
    return ""


async def adobe_firefly_generate(prompt: str, width: int = 1024, height: int = 1024, n: int = 1) -> dict:
    """Generate image using Adobe Firefly."""
    token = await _adobe_token()
    if not token:
        return {"error": "Adobe credentials not configured"}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{ADOBE_API}/pie/precheckv2/prompt",
            headers={
                "Authorization": f"Bearer {token}",
                "x-api-key": ADOBE_CLIENT_ID,
                "Content-Type": "application/json",
            },
            json={"prompt": prompt},
        )
        r2 = await client.post(
            "https://firefly-api.adobe.io/v3/images/generate",
            headers={
                "Authorization": f"Bearer {token}",
                "x-api-key": ADOBE_CLIENT_ID,
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "n": n,
                "size": {"width": width, "height": height},
            },
        )
        if r2.status_code in (200, 201):
            return {"images": r2.json(), "tool": "adobe_firefly", "action": "generate"}
        return {"error": r2.text}


async def adobe_remove_background(image_url: str) -> dict:
    """Remove background using Adobe Photoshop API."""
    token = await _adobe_token()
    if not token:
        return {"error": "Adobe credentials not configured"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://image.adobe.io/sensei/cutout",
            headers={
                "Authorization": f"Bearer {token}",
                "x-api-key": ADOBE_CLIENT_ID,
                "Content-Type": "application/json",
            },
            json={"input": {"href": image_url, "storage": "external"}},
        )
        if r.status_code in (200, 201, 202):
            return {"result": r.json(), "tool": "adobe_photoshop", "action": "remove_bg"}
        return {"error": r.text}


async def adobe_generative_fill(image_url: str, mask_url: str, prompt: str) -> dict:
    """Generative fill using Adobe Firefly."""
    token = await _adobe_token()
    if not token:
        return {"error": "Adobe credentials not configured"}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            "https://firefly-api.adobe.io/v3/images/fill",
            headers={
                "Authorization": f"Bearer {token}",
                "x-api-key": ADOBE_CLIENT_ID,
                "Content-Type": "application/json",
            },
            json={
                "image": {"source": {"url": image_url}},
                "mask": {"source": {"url": mask_url}},
                "prompt": prompt,
            },
        )
        if r.status_code in (200, 201):
            return {"result": r.json(), "tool": "adobe_firefly", "action": "fill"}
        return {"error": r.text}


# ── Combined tool map ────────────────────────────────────────────────────

DESIGN_TOOL_MAP = {
    "canva_create": canva_create_design,
    "canva_upload": canva_upload_asset,
    "canva_export": canva_export_design,
    "canva_list": canva_list_designs,
    "figma_file": figma_get_file,
    "figma_export": figma_export_nodes,
    "figma_components": figma_get_components,
    "figma_styles": figma_get_styles,
    "figma_comment": figma_post_comment,
    "adobe_generate": adobe_firefly_generate,
    "adobe_remove_bg": adobe_remove_background,
    "adobe_fill": adobe_generative_fill,
}
