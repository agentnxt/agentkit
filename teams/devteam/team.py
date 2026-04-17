"""
EngineeringTeam — orchestrates the full software engineering workflow.

Flow:
  1. Requirement → AgentCode writes HLD
  2. Claude Architect reviews architecture
  3. AgentCode writes code + tests
  4. Claude Reviewer does PR review
  5. Claude Security Auditor runs vulnerability check
  6. Claude Merge Manager makes final decision
  7. If approved → merge. If blocked → loop back to step 3.
"""

import json
from dataclasses import dataclass, field
from eng_team.agents import (
    AgentCodeDeveloper,
    ClaudeArchitect,
    ClaudeReviewer,
    ClaudeSecurityAuditor,
    ClaudeMergeManager,
    AgentResult,
)


@dataclass
class PipelineResult:
    requirement: str
    hld: AgentResult = None
    architecture_review: AgentResult = None
    code: AgentResult = None
    tests: AgentResult = None
    code_review: AgentResult = None
    security_audit: AgentResult = None
    merge_decision: AgentResult = None
    iterations: int = 0
    final_status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "requirement": self.requirement,
            "iterations": self.iterations,
            "final_status": self.final_status,
            "stages": {
                "hld": {"output": self.hld.output[:500] if self.hld else None},
                "architecture_review": {
                    "approved": self.architecture_review.approved if self.architecture_review else None,
                    "issues": self.architecture_review.issues if self.architecture_review else [],
                },
                "code": {"files_changed": self.code.files_changed if self.code else []},
                "tests": {"files_changed": self.tests.files_changed if self.tests else []},
                "code_review": {
                    "approved": self.code_review.approved if self.code_review else None,
                    "issues": self.code_review.issues if self.code_review else [],
                },
                "security_audit": {
                    "approved": self.security_audit.approved if self.security_audit else None,
                    "issues": self.security_audit.issues if self.security_audit else [],
                },
                "merge_decision": {
                    "approved": self.merge_decision.approved if self.merge_decision else None,
                    "output": self.merge_decision.output[:500] if self.merge_decision else None,
                },
            },
        }


class EngineeringTeam:
    """Full AI engineering team orchestrator."""

    def __init__(self, repo: str = "", max_iterations: int = 3, verbose: bool = True):
        self.repo = repo
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.developer = AgentCodeDeveloper()
        self.architect = ClaudeArchitect()
        self.reviewer = ClaudeReviewer()
        self.security = ClaudeSecurityAuditor()
        self.merger = ClaudeMergeManager()

    def _log(self, stage: str, msg: str):
        if self.verbose:
            print(f"[{stage}] {msg}")

    async def run(self, requirement: str, context: str = "") -> PipelineResult:
        result = PipelineResult(requirement=requirement)

        # Stage 1: HLD
        self._log("DEVELOPER", "Writing High-Level Design...")
        result.hld = await self.developer.write_hld(requirement, context)
        self._log("DEVELOPER", f"HLD complete ({len(result.hld.output)} chars)")

        # Stage 2: Architecture Review
        self._log("ARCHITECT", "Reviewing architecture...")
        result.architecture_review = await self.architect.review_architecture(
            result.hld.output, context
        )
        self._log("ARCHITECT", f"Architecture: {'APPROVED' if result.architecture_review.approved else 'NEEDS WORK'}")

        if not result.architecture_review.approved:
            self._log("ARCHITECT", f"Issues: {result.architecture_review.issues}")
            feedback = result.architecture_review.output
            self._log("DEVELOPER", "Revising HLD based on feedback...")
            result.hld = await self.developer.write_hld(
                f"{requirement}\n\nArchitect feedback:\n{feedback}", context
            )

        # Stage 3-6: Code → Review → Security → Merge (with retry loop)
        for iteration in range(self.max_iterations):
            result.iterations = iteration + 1
            self._log("ITERATION", f"--- Iteration {iteration + 1} ---")

            # Stage 3: Write Code
            self._log("DEVELOPER", "Writing code...")
            spec = f"HLD:\n{result.hld.output}\n\nRequirement:\n{requirement}"
            if iteration > 0 and result.code_review:
                spec += f"\n\nPrevious review feedback:\n{result.code_review.output}"
            result.code = await self.developer.write_code(spec, self.repo)
            self._log("DEVELOPER", f"Code written. Files: {result.code.files_changed}")

            # Stage 3b: Write Tests
            self._log("DEVELOPER", "Writing tests...")
            result.tests = await self.developer.write_tests(result.code.output, self.repo)
            self._log("DEVELOPER", f"Tests written. Files: {result.tests.files_changed}")

            # Stage 4: PR Review
            self._log("REVIEWER", "Reviewing code...")
            result.code_review = await self.reviewer.review_pr(
                diff=result.code.output,
                pr_description=requirement,
            )
            self._log("REVIEWER", f"Review: {'APPROVED' if result.code_review.approved else 'CHANGES REQUESTED'}")

            if not result.code_review.approved:
                self._log("REVIEWER", f"Issues: {result.code_review.issues}")
                continue

            # Stage 5: Security Audit
            self._log("SECURITY", "Running security audit...")
            result.security_audit = await self.security.audit(
                code=result.code.output,
                context=requirement,
            )
            self._log("SECURITY", f"Security: {'PASSED' if result.security_audit.approved else 'FAILED'}")

            if not result.security_audit.approved:
                self._log("SECURITY", f"Vulnerabilities: {result.security_audit.issues}")
                continue

            # Stage 6: Merge Decision
            self._log("MERGE MANAGER", "Making merge decision...")
            result.merge_decision = await self.merger.decide_merge(
                pr_description=requirement,
                architecture_review=result.architecture_review,
                code_review=result.code_review,
                security_audit=result.security_audit,
            )
            self._log("MERGE MANAGER", f"Decision: {'MERGE' if result.merge_decision.approved else 'BLOCKED'}")

            if result.merge_decision.approved:
                result.final_status = "merged"
                self._log("DONE", "PR merged successfully!")
                return result
            else:
                self._log("MERGE MANAGER", "Blocked — sending back for fixes")
                continue

        result.final_status = "max_iterations_reached"
        self._log("DONE", f"Max iterations ({self.max_iterations}) reached. Manual review needed.")
        return result

    async def quick_review(self, diff: str, description: str = "") -> dict:
        """Just do a code review without the full pipeline."""
        review = await self.reviewer.review_pr(diff, description)
        security = await self.security.audit(diff)
        return {
            "code_review": {"approved": review.approved, "issues": review.issues, "output": review.output},
            "security": {"approved": security.approved, "issues": security.issues, "output": security.output},
        }

    async def design_only(self, requirement: str, context: str = "") -> dict:
        """Just do HLD + architecture review."""
        hld = await self.developer.write_hld(requirement, context)
        arch = await self.architect.review_architecture(hld.output, context)
        tech = await self.architect.decide_tech_stack(requirement)
        return {
            "hld": hld.output,
            "architecture_review": {"approved": arch.approved, "issues": arch.issues, "output": arch.output},
            "tech_stack": tech.output,
        }
