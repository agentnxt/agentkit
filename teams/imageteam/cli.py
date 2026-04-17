"""CLI for Image Agent."""

import click
import asyncio
import json


@click.group()
@click.version_option()
def main():
    """Image Agent — generate, edit, upscale, remove bg, describe."""
    pass


@main.command()
@click.argument("prompt")
@click.option("--model", default="auto", help="Model: sdxl, flux, fal, auto")
@click.option("--width", default=1024)
@click.option("--height", default=1024)
@click.option("--output", "-o", default="output.png", help="Output file")
def generate(prompt, model, width, height, output):
    """Generate an image from text."""
    from image_agent.agent import ImageAgent
    agent = ImageAgent()
    result = asyncio.run(agent.generate(prompt, model, width, height))
    print(json.dumps(result, indent=2))


@main.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8900)
def serve(host, port):
    """Start the Image Agent API server."""
    import uvicorn
    from image_agent.api import create_app
    app = create_app()
    uvicorn.run(app, host=host, port=port)


@main.command()
@click.argument("image_path")
def describe(image_path):
    """Describe an image."""
    import base64
    from image_agent.agent import ImageAgent
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    agent = ImageAgent()
    result = asyncio.run(agent.describe(b64))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
