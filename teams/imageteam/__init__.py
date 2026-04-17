"""Image Agent — generate, edit, upscale, remove bg, describe. Routes to any model/tool."""

__version__ = "0.1.0"

from image_agent.agent import ImageAgent
from image_agent.api import create_app

__all__ = ["ImageAgent", "create_app"]
