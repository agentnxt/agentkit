"""Engineering Agent Team — AI-powered software engineering workflow."""

__version__ = "0.1.0"

from eng_team.team import EngineeringTeam
from eng_team.agents import (
    AgentCodeDeveloper,
    ClaudeArchitect,
    ClaudeReviewer,
    ClaudeSecurityAuditor,
    ClaudeMergeManager,
)

__all__ = [
    "EngineeringTeam",
    "AgentCodeDeveloper",
    "ClaudeArchitect",
    "ClaudeReviewer",
    "ClaudeSecurityAuditor",
    "ClaudeMergeManager",
]
