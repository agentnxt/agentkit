"""AgentCrew CLI — run crews from the command line."""

import click
import asyncio
import json


@click.group()
@click.version_option()
def main():
    """AgentCrew — CLI, SDK, API, MCP in one package."""
    pass


@main.command()
@click.option("--host", default="0.0.0.0", help="API host")
@click.option("--port", default=8501, help="API port")
def serve(host, port):
    """Start the AgentCrew API server."""
    import uvicorn
    from agentcrew.api import create_app
    app = create_app()
    uvicorn.run(app, host=host, port=port)


@main.command()
@click.option("--host", default="0.0.0.0", help="MCP server host")
@click.option("--port", default=3000, help="MCP server port")
def mcp(host, port):
    """Start the AgentCrew MCP server."""
    from agentcrew.mcp_server import start_mcp
    start_mcp(host=host, port=port)


@main.command()
@click.argument("crew_file")
@click.option("--input", "-i", multiple=True, help="Key=value inputs")
def run(crew_file, input):
    """Run a crew definition from a YAML/JSON file."""
    import yaml

    with open(crew_file) as f:
        if crew_file.endswith(".json"):
            spec = json.load(f)
        else:
            spec = yaml.safe_load(f)

    from agentcrew.sdk import Agent, Task, Crew

    agents = {a["name"]: Agent(**a) for a in spec.get("agents", [])}
    tasks = [
        Task(
            description=t["description"],
            agent=agents[t["agent"]],
            expected_output=t.get("expected_output", ""),
        )
        for t in spec.get("tasks", [])
    ]
    crew = Crew(agents=list(agents.values()), tasks=tasks, verbose=True)

    inputs = dict(kv.split("=", 1) for kv in input)
    result = asyncio.run(crew.kickoff(inputs))
    print(json.dumps(result, indent=2))


@main.command()
def version():
    """Show version."""
    from agentcrew import __version__
    print(f"agentcrew {__version__}")


if __name__ == "__main__":
    main()
