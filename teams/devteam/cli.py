"""CLI for the Engineering Agent Team."""

import click
import asyncio
import json


@click.group()
@click.version_option()
def main():
    """Engineering Agent Team — AI-powered software engineering."""
    pass


@main.command()
@click.argument("requirement")
@click.option("--repo", default="", help="GitHub repo URL")
@click.option("--context", default="", help="Additional context")
@click.option("--max-iterations", default=3, help="Max review iterations")
def build(requirement, repo, context, max_iterations):
    """Run the full engineering pipeline: HLD → Code → Review → Security → Merge."""
    from eng_team.team import EngineeringTeam
    team = EngineeringTeam(repo=repo, max_iterations=max_iterations)
    result = asyncio.run(team.run(requirement, context))
    print(json.dumps(result.to_dict(), indent=2))


@main.command()
@click.argument("diff_file", type=click.File("r"))
@click.option("--description", default="", help="PR description")
def review(diff_file, description):
    """Review a diff/PR for code quality and security."""
    from eng_team.team import EngineeringTeam
    team = EngineeringTeam()
    diff = diff_file.read()
    result = asyncio.run(team.quick_review(diff, description))
    print(json.dumps(result, indent=2))


@main.command()
@click.argument("requirement")
@click.option("--context", default="", help="Additional context")
def design(requirement, context):
    """Generate HLD + architecture review + tech stack decision."""
    from eng_team.team import EngineeringTeam
    team = EngineeringTeam()
    result = asyncio.run(team.design_only(requirement, context))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
