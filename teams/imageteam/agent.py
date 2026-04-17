"""
ImageAgent — LangGraph-based agent that routes to the right image tool.

State graph:
  START → classify_intent → route_to_tool → execute_tool → format_result → END
                                  ↑                              |
                                  └── retry (if failed) ─────────┘
"""

import os
import json
import operator
from typing import Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from image_agent.tools import TOOL_MAP
from image_agent.memory import ImageMemory


ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


class ImageState(TypedDict):
    input: str
    image_b64: str
    intent: str
    tool: str
    tool_args: dict
    result: dict
    error: str
    retries: int


INTENT_MAP = {
    "generate": ["generate_sdxl", "generate_flux", "generate_fal"],
    "edit": ["edit_image"],
    "upscale": ["upscale_image"],
    "remove_background": ["remove_background"],
    "describe": ["describe_image"],
    "transform": ["transform_image"],
}


def classify_intent(state: ImageState) -> ImageState:
    """Use Claude to classify what the user wants."""
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=ANTHROPIC_API_KEY)
    response = llm.invoke([
        SystemMessage(content="""Classify this image request into exactly one intent:
- generate: create new image from text
- edit: modify existing image
- upscale: increase resolution
- remove_background: remove bg from image
- describe: describe/caption an image
- transform: resize, crop, filter

Also extract key parameters. Respond as JSON:
{"intent": "...", "prompt": "...", "model_preference": "sdxl|flux|fal|auto", "width": 1024, "height": 1024}"""),
        HumanMessage(content=state["input"]),
    ])

    import json
    try:
        parsed = json.loads(response.content)
    except:
        parsed = {"intent": "generate", "prompt": state["input"], "model_preference": "auto"}

    intent = parsed.get("intent", "generate")
    model_pref = parsed.get("model_preference", "auto")

    if intent == "generate":
        if model_pref == "flux":
            tool = "generate_flux"
        elif model_pref == "fal":
            tool = "generate_fal"
        elif model_pref == "sdxl":
            tool = "generate_sdxl"
        else:
            tool = "generate_fal"
    else:
        tools = INTENT_MAP.get(intent, ["generate_fal"])
        tool = tools[0]

    state["intent"] = intent
    state["tool"] = tool
    state["tool_args"] = {
        "prompt": parsed.get("prompt", state["input"]),
        "width": parsed.get("width", 1024),
        "height": parsed.get("height", 1024),
    }
    if state.get("image_b64") and intent in ("edit", "upscale", "remove_background", "describe"):
        state["tool_args"]["image_b64"] = state["image_b64"]

    return state


async def execute_tool(state: ImageState) -> ImageState:
    """Execute the selected tool."""
    tool_fn = TOOL_MAP.get(state["tool"])
    if not tool_fn:
        state["error"] = f"Unknown tool: {state['tool']}"
        return state

    try:
        result = await tool_fn(**state["tool_args"])
        if "error" in result:
            state["error"] = result["error"]
            state["retries"] = state.get("retries", 0) + 1
        else:
            state["result"] = result
            state["error"] = ""
    except Exception as e:
        state["error"] = str(e)
        state["retries"] = state.get("retries", 0) + 1

    return state


def should_retry(state: ImageState) -> Literal["retry", "done"]:
    """Decide whether to retry with a different tool."""
    if state.get("error") and state.get("retries", 0) < 3:
        intent = state.get("intent", "generate")
        available = INTENT_MAP.get(intent, [])
        current = state.get("tool", "")
        remaining = [t for t in available if t != current]
        if remaining:
            state["tool"] = remaining[0]
            return "retry"
    return "done"


def format_result(state: ImageState) -> ImageState:
    """Format the final result."""
    if state.get("error"):
        state["result"] = {"status": "failed", "error": state["error"], "retries": state.get("retries", 0)}
    else:
        state["result"]["status"] = "success"
        state["result"]["intent"] = state.get("intent", "")
        state["result"]["tool_used"] = state.get("tool", "")
    return state


def build_graph() -> StateGraph:
    """Build the LangGraph state graph."""
    graph = StateGraph(ImageState)

    graph.add_node("classify", classify_intent)
    graph.add_node("execute", execute_tool)
    graph.add_node("format", format_result)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "execute")
    graph.add_conditional_edges("execute", should_retry, {"retry": "execute", "done": "format"})
    graph.add_edge("format", END)

    return graph.compile()


class ImageAgent:
    """High-level image agent interface with memory."""

    def __init__(self, user_id: str = "", session_id: str = "", use_memory: bool = True):
        self.graph = build_graph()
        self.memory = ImageMemory(user_id=user_id, session_id=session_id) if use_memory else None

    async def run(self, prompt: str, image_b64: str = "") -> dict:
        if self.memory:
            await self.memory.save_input(prompt)
            past = await self.memory.recall(prompt, limit=3)
            if past:
                prompt += f"\n\n[Context from past sessions: {json.dumps([p.get('prompt','') for p in past])}]"
        state = ImageState(
            input=prompt,
            image_b64=image_b64,
            intent="",
            tool="",
            tool_args={},
            result={},
            error="",
            retries=0,
        )
        result = await self.graph.ainvoke(state)
        output = result.get("result", {})

        if self.memory and output.get("status") == "success":
            await self.memory.remember(
                prompt=prompt,
                tool=output.get("tool_used", ""),
                result=json.dumps(output)[:500],
            )

        return output

    async def generate(self, prompt: str, model: str = "auto", width: int = 1024, height: int = 1024) -> dict:
        return await self.run(f"Generate image: {prompt}. Model: {model}. Size: {width}x{height}")

    async def edit(self, image_b64: str, prompt: str) -> dict:
        return await self.run(f"Edit image: {prompt}", image_b64=image_b64)

    async def upscale(self, image_b64: str, scale: int = 2) -> dict:
        return await self.run(f"Upscale image {scale}x", image_b64=image_b64)

    async def remove_bg(self, image_b64: str) -> dict:
        return await self.run("Remove background from image", image_b64=image_b64)

    async def describe(self, image_b64: str) -> dict:
        return await self.run("Describe this image in detail", image_b64=image_b64)
