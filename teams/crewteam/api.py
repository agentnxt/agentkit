"""AgentCrew API — FastAPI server for running crews via HTTP."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional


class AgentSpec(BaseModel):
    name: str
    role: str
    goal: str
    backstory: str = ""
    model: str = "ollama/qwen3:30b-a3b"


class TaskSpec(BaseModel):
    description: str
    agent: str
    expected_output: str = ""


class CrewRequest(BaseModel):
    agents: list[AgentSpec]
    tasks: list[TaskSpec]
    inputs: dict = {}
    verbose: bool = False


def create_app() -> FastAPI:
    app = FastAPI(title="AgentCrew API", version="0.1.0")

    @app.post("/crew/run")
    async def run_crew(req: CrewRequest):
        from agentcrew.sdk import Agent, Task, Crew

        agents = {a.name: Agent(**a.model_dump()) for a in req.agents}
        tasks = []
        for t in req.tasks:
            if t.agent not in agents:
                raise HTTPException(400, f"Agent '{t.agent}' not found")
            tasks.append(Task(
                description=t.description,
                agent=agents[t.agent],
                expected_output=t.expected_output,
            ))

        crew = Crew(agents=list(agents.values()), tasks=tasks, verbose=req.verbose)
        result = await crew.kickoff(req.inputs)
        return result

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "agentcrew"}

    return app
