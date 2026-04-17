"""
Image tools — each tool wraps an external model/service.
The agent routes to the right tool based on the task.
"""

import os
import httpx
import base64
from io import BytesIO


COMFYUI_URL = os.environ.get("COMFYUI_URL", "")
AUTOMATIC1111_URL = os.environ.get("AUTOMATIC1111_URL", "")
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
FAL_KEY = os.environ.get("FAL_KEY", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
IMAGOR_URL = os.environ.get("IMAGOR_URL", "")


async def generate_sdxl(prompt: str, negative_prompt: str = "", width: int = 1024, height: int = 1024, steps: int = 30) -> dict:
    """Generate image using Stable Diffusion XL via Automatic1111 API."""
    if not AUTOMATIC1111_URL:
        return {"error": "AUTOMATIC1111_URL not configured"}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{AUTOMATIC1111_URL}/sdapi/v1/txt2img", json={
            "prompt": prompt,
            "negative_prompt": negative_prompt or "blurry, bad quality, distorted",
            "width": width, "height": height,
            "steps": steps, "cfg_scale": 7,
        })
        if r.status_code == 200:
            images = r.json().get("images", [])
            return {"images": images, "model": "sdxl", "count": len(images)}
        return {"error": r.text}


async def generate_flux(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    """Generate image using FLUX via ComfyUI or Replicate."""
    if COMFYUI_URL:
        async with httpx.AsyncClient(timeout=180) as client:
            workflow = {
                "prompt": {
                    "3": {"class_type": "KSampler", "inputs": {"seed": -1, "steps": 20, "cfg": 1.0}},
                }
            }
            r = await client.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
            if r.status_code == 200:
                return {"prompt_id": r.json().get("prompt_id"), "model": "flux-comfyui"}

    if REPLICATE_TOKEN:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {REPLICATE_TOKEN}"},
                json={
                    "model": "black-forest-labs/flux-schnell",
                    "input": {"prompt": prompt, "width": width, "height": height},
                },
            )
            if r.status_code in (200, 201):
                return {"prediction": r.json(), "model": "flux-replicate"}

    return {"error": "No FLUX backend configured (set COMFYUI_URL or REPLICATE_API_TOKEN)"}


async def generate_fal(prompt: str, model: str = "fal-ai/flux/schnell", width: int = 1024, height: int = 1024) -> dict:
    """Generate image using fal.ai API."""
    if not FAL_KEY:
        return {"error": "FAL_KEY not configured"}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"https://queue.fal.run/{model}",
            headers={"Authorization": f"Key {FAL_KEY}"},
            json={"prompt": prompt, "image_size": {"width": width, "height": height}},
        )
        if r.status_code in (200, 201):
            return {"result": r.json(), "model": model}
        return {"error": r.text}


async def edit_image(image_b64: str, prompt: str, mask_b64: str = "") -> dict:
    """Edit/inpaint an image using img2img."""
    if not AUTOMATIC1111_URL:
        return {"error": "AUTOMATIC1111_URL not configured"}
    async with httpx.AsyncClient(timeout=120) as client:
        payload = {
            "init_images": [image_b64],
            "prompt": prompt,
            "denoising_strength": 0.7,
            "steps": 30,
        }
        if mask_b64:
            payload["mask"] = mask_b64
        r = await client.post(f"{AUTOMATIC1111_URL}/sdapi/v1/img2img", json=payload)
        if r.status_code == 200:
            return {"images": r.json().get("images", []), "tool": "img2img"}
        return {"error": r.text}


async def upscale_image(image_b64: str, scale: int = 2) -> dict:
    """Upscale image using Real-ESRGAN via Automatic1111."""
    if not AUTOMATIC1111_URL:
        return {"error": "AUTOMATIC1111_URL not configured"}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{AUTOMATIC1111_URL}/sdapi/v1/extra-single-image", json={
            "image": image_b64,
            "upscaler_1": "R-ESRGAN 4x+",
            "upscaling_resize": scale,
        })
        if r.status_code == 200:
            return {"image": r.json().get("image", ""), "tool": "upscale"}
        return {"error": r.text}


async def remove_background(image_b64: str) -> dict:
    """Remove background using rembg."""
    try:
        from rembg import remove
        from PIL import Image

        img_data = base64.b64decode(image_b64)
        img = Image.open(BytesIO(img_data))
        result = remove(img)
        buf = BytesIO()
        result.save(buf, format="PNG")
        return {"image": base64.b64encode(buf.getvalue()).decode(), "tool": "rembg"}
    except ImportError:
        return {"error": "rembg not installed. pip install rembg"}


async def describe_image(image_b64: str) -> dict:
    """Describe image using vision model (Ollama or Claude)."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json={
            "model": "llava:13b",
            "prompt": "Describe this image in detail. Include: subject, composition, colors, mood, style.",
            "images": [image_b64],
            "stream": False,
        })
        if r.status_code == 200:
            return {"description": r.json().get("response", ""), "tool": "llava"}
        return {"error": r.text}


async def transform_image(image_url: str, operations: str = "") -> dict:
    """Transform image using Imagor (resize, crop, filters)."""
    if not IMAGOR_URL:
        return {"error": "IMAGOR_URL not configured"}
    transform_url = f"{IMAGOR_URL}/unsafe/{operations}/{image_url}"
    return {"url": transform_url, "tool": "imagor"}


from image_agent.tools_design import DESIGN_TOOL_MAP
from image_agent.tools_sources import SOURCE_TOOL_MAP
from image_agent.tools_publish import PUBLISH_TOOL_MAP
from image_agent.tools_content import CONTENT_TOOL_MAP

TOOL_MAP = {
    "generate_sdxl": generate_sdxl,
    "generate_flux": generate_flux,
    "generate_fal": generate_fal,
    "edit_image": edit_image,
    "upscale_image": upscale_image,
    "remove_background": remove_background,
    "describe_image": describe_image,
    "transform_image": transform_image,
    **DESIGN_TOOL_MAP,
    **SOURCE_TOOL_MAP,
    **PUBLISH_TOOL_MAP,
    **CONTENT_TOOL_MAP,
}
