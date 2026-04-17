"""FastAPI server for the Image Agent."""

from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import base64


class GenerateRequest(BaseModel):
    prompt: str
    model: str = "auto"
    width: int = 1024
    height: int = 1024


class EditRequest(BaseModel):
    prompt: str
    image: str
    mask: str = ""


def create_app() -> FastAPI:
    app = FastAPI(title="Image Agent", version="0.1.0", description="AI Image Agent — generate, edit, upscale, remove bg, describe")

    @app.post("/generate")
    async def generate(req: GenerateRequest):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.generate(req.prompt, req.model, req.width, req.height)

    @app.post("/edit")
    async def edit(req: EditRequest):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.edit(req.image, req.prompt)

    @app.post("/upscale")
    async def upscale(image: str = Form(...), scale: int = Form(2)):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.upscale(image, scale)

    @app.post("/remove-bg")
    async def remove_bg(image: str = Form(...)):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.remove_bg(image)

    @app.post("/describe")
    async def describe(image: str = Form(...)):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.describe(image)

    @app.post("/auto")
    async def auto(prompt: str = Form(...), image: Optional[str] = Form(None)):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.run(prompt, image_b64=image or "")

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "image-agent"}

    @app.get("/models")
    async def models():
        return {
            "generation": ["sdxl", "flux", "fal"],
            "editing": ["img2img", "inpaint"],
            "upscale": ["real-esrgan"],
            "vision": ["llava"],
            "background": ["rembg"],
            "transform": ["imagor"],
        }

    return app
