"""
Individual agents in the engineering team.

AgentCode (OpenHands) → writes code, tests, HLD
Claude Code → reviews, architecture, security, merge
"""

import os
import httpx
from dataclasses import dataclass, field
from typing import Optional
from anthropic import Anthropic


AGENTCODE_URL = os.environ.get("AGENTCODE_URL", "https://code.agnxxt.com")
IDENTITY_URL = os.environ.get("IDENTITY_URL", "https://api.unboxd.cloud/identity")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


@dataclass
class AgentResult:
    agent: str
    task: str
    output: str
    files_changed: list[str] = field(default_factory=list)
    approved: bool = False
    issues: list[str] = field(default_factory=list)


class BaseAgent:
    def __init__(self, name: str, model: str = "claude-sonnet-4-20250514"):
        self.name = name
        self.model = model
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

    async def _call_claude(self, system: str, prompt: str, max_tokens: int = 4096) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def _call_agentcode(self, task: str, repo: str = "") -> dict:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                f"{AGENTCODE_URL}/api/conversations",
                json={
                    "message": task,
                    "repository": repo,
                },
            )
            if r.status_code == 200:
                return r.json()
            return {"error": r.text}


class AgentCodeDeveloper(BaseAgent):
    """Writes code, test cases, HLD using AgentCode (OpenHands)."""

    def __init__(self):
        super().__init__("developer", model="claude-sonnet-4-20250514")

    async def write_hld(self, requirement: str, context: str = "") -> AgentResult:
        output = await self._call_claude(
            system="""You are a senior software architect. Write a High-Level Design document.
Include: overview, components, data flow, API contracts, technology choices, trade-offs.""",
            prompt=f"Requirement:\n{requirement}\n\nContext:\n{context}",
            max_tokens=8192,
        )
        return AgentResult(agent=self.name, task="hld", output=output)

    async def write_code(self, spec: str, repo: str = "") -> AgentResult:
        result = await self._call_agentcode(
            task=f"Implement the following specification. Write clean, tested code.\n\n{spec}",
            repo=repo,
        )
        return AgentResult(
            agent=self.name,
            task="code",
            output=str(result),
            files_changed=result.get("files_changed", []),
        )

    async def write_tests(self, code_context: str, repo: str = "") -> AgentResult:
        result = await self._call_agentcode(
            task=f"""Write comprehensive test cases for the following code.
Include: unit tests, edge cases, error handling, integration tests.

{code_context}""",
            repo=repo,
        )
        return AgentResult(
            agent=self.name,
            task="tests",
            output=str(result),
            files_changed=result.get("files_changed", []),
        )

    async def design_api(self, requirement: str) -> AgentResult:
        output = await self._call_claude(
            system="You are an API designer. Design RESTful APIs following OpenAPI 3.0 spec.",
            prompt=f"Design APIs for:\n{requirement}",
            max_tokens=8192,
        )
        return AgentResult(agent=self.name, task="api_design", output=output)


class ClaudeArchitect(BaseAgent):
    """Reviews architecture, decides engineering approach."""

    def __init__(self):
        super().__init__("architect", model="claude-opus-4-20250514")

    async def review_architecture(self, hld: str, codebase_context: str = "") -> AgentResult:
        output = await self._call_claude(
            system="""You are a principal engineer reviewing architecture decisions.
Evaluate: scalability, security, maintainability, cost, vendor lock-in.
Be specific about what to change and why.""",
            prompt=f"HLD to review:\n{hld}\n\nCodebase context:\n{codebase_context}",
            max_tokens=4096,
        )
        issues = [line.strip("- ") for line in output.split("\n") if line.strip().startswith("- ")]
        approved = "approved" in output.lower() and "not approved" not in output.lower()
        return AgentResult(
            agent=self.name, task="architecture_review", output=output,
            approved=approved, issues=issues,
        )

    async def decide_tech_stack(self, requirement: str, constraints: str = "") -> AgentResult:
        output = await self._call_claude(
            system="""You are a CTO making technology decisions.
Consider: team expertise, scalability, licensing (prefer Apache 2.0/MIT), ecosystem, cost.
Return a clear decision with rationale for each choice.""",
            prompt=f"Requirement:\n{requirement}\n\nConstraints:\n{constraints}",
        )
        return AgentResult(agent=self.name, task="tech_decision", output=output)


class ClaudeReviewer(BaseAgent):
    """Does PR reviews — code quality, patterns, bugs."""

    def __init__(self):
        super().__init__("reviewer", model="claude-opus-4-20250514")

    async def review_pr(self, diff: str, pr_description: str = "") -> AgentResult:
        output = await self._call_claude(
            system="""You are a senior code reviewer. Review this PR for:
1. Correctness — logic bugs, edge cases, race conditions
2. Security — injection, auth bypass, data exposure
3. Performance — N+1 queries, memory leaks, unnecessary allocations
4. Maintainability — naming, structure, complexity
5. Test coverage — are critical paths tested?

For each issue, specify: file, line (if possible), severity (critical/major/minor), fix.
End with APPROVED or CHANGES_REQUESTED.""",
            prompt=f"PR Description:\n{pr_description}\n\nDiff:\n{diff}",
            max_tokens=8192,
        )
        approved = "APPROVED" in output and "CHANGES_REQUESTED" not in output
        issues = []
        for line in output.split("\n"):
            stripped = line.strip()
            if any(sev in stripped.lower() for sev in ["critical", "major", "minor"]):
                issues.append(stripped)
        return AgentResult(
            agent=self.name, task="pr_review", output=output,
            approved=approved, issues=issues,
        )

    async def review_tests(self, test_code: str, source_code: str) -> AgentResult:
        output = await self._call_claude(
            system="""Review test quality. Check:
- Coverage of happy path and error paths
- Edge cases (empty, null, boundary values)
- Mock correctness (are mocks realistic?)
- Test isolation (no shared state)
- Missing tests for critical logic""",
            prompt=f"Source code:\n{source_code}\n\nTests:\n{test_code}",
        )
        return AgentResult(agent=self.name, task="test_review", output=output)


class ClaudeSecurityAuditor(BaseAgent):
    """Vulnerability testing and security audit."""

    def __init__(self):
        super().__init__("security_auditor", model="claude-opus-4-20250514")

    async def audit(self, code: str, context: str = "") -> AgentResult:
        output = await self._call_claude(
            system="""You are a security engineer performing a code audit. Check for:
1. OWASP Top 10 vulnerabilities
2. Authentication/authorization bypasses
3. Injection vulnerabilities (SQL, command, XSS, SSTI)
4. Secrets/credentials in code
5. Insecure dependencies
6. Data exposure (PII, tokens in logs)
7. Race conditions and TOCTOU bugs
8. Cryptographic weaknesses

Rate each finding: CRITICAL / HIGH / MEDIUM / LOW
Provide specific remediation steps.""",
            prompt=f"Code to audit:\n{code}\n\nContext:\n{context}",
            max_tokens=8192,
        )
        issues = []
        for line in output.split("\n"):
            stripped = line.strip()
            if any(sev in stripped for sev in ["CRITICAL", "HIGH", "MEDIUM"]):
                issues.append(stripped)
        approved = not any("CRITICAL" in i or "HIGH" in i for i in issues)
        return AgentResult(
            agent=self.name, task="security_audit", output=output,
            approved=approved, issues=issues,
        )


class ClaudeMergeManager(BaseAgent):
    """Final approval and merge decision."""

    def __init__(self):
        super().__init__("merge_manager", model="claude-opus-4-20250514")

    async def decide_merge(
        self,
        pr_description: str,
        architecture_review: AgentResult,
        code_review: AgentResult,
        security_audit: AgentResult,
        test_results: str = "",
    ) -> AgentResult:
        summary = f"""PR: {pr_description}

Architecture Review ({architecture_review.agent}):
  Approved: {architecture_review.approved}
  Issues: {architecture_review.issues}

Code Review ({code_review.agent}):
  Approved: {code_review.approved}
  Issues: {code_review.issues}

Security Audit ({security_audit.agent}):
  Approved: {security_audit.approved}
  Issues: {security_audit.issues}

Test Results: {test_results}"""

        output = await self._call_claude(
            system="""You are the engineering manager making the final merge decision.
Based on all reviews, decide: MERGE, MERGE_WITH_FOLLOWUP, or BLOCK.

MERGE — all clear, ship it.
MERGE_WITH_FOLLOWUP — minor issues, merge now, create tickets for fixes.
BLOCK — critical issues, must fix before merge.

Explain your decision. List any follow-up tickets to create.""",
            prompt=summary,
        )
        approved = "MERGE" in output and "BLOCK" not in output
        return AgentResult(
            agent=self.name, task="merge_decision", output=output,
            approved=approved,
        )
