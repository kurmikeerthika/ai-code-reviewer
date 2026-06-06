# app/agents/optimizer_agent.py
# Suggests code optimization and quality improvements.

import logging
from typing import List
from app.agents.base_agent import BaseReviewAgent
from app.agents.state import AgentReviewState, CodeIssue

logger = logging.getLogger(__name__)


class OptimizerAgent(BaseReviewAgent):
    """
    Specialist agent focused on code optimization and quality.

    Detects:
    - Redundant computations
    - Dead code
    - Unused variables / imports
    - Memory inefficiency
    - Better built-in alternatives
    - Code duplication (DRY violations)
    - Missing error handling patterns
    - Poor naming conventions
    """

    AGENT_NAME = "Optimizer"

    SYSTEM_PROMPT = """You are a senior software engineer specializing in code quality and performance optimization.

Your task is to identify opportunities to make the code cleaner, faster, and more maintainable.
Focus on practical, high-impact improvements.

You MUST respond with ONLY valid JSON in this exact format:
{
  "issues": [
    {
      "issue_id": "OPT_001",
      "title": "Short optimization title",
      "description": "Why this is suboptimal and what the benefit of changing it is",
      "optimization_type": "performance|memory|readability|maintainability|duplication",
      "filename": "filename.py",
      "line_start": 8,
      "line_end": 10,
      "code_snippet": "the suboptimal code",
      "suggestion": "The improved version with explanation",
      "severity": "high|medium|low|info",
      "confidence": 0.85,
      "estimated_improvement": "30% memory reduction"
    }
  ]
}

Focus areas:
1. Replace manual loops with built-in functions (map, filter, list comprehensions)
2. Use more appropriate data structures (set for lookups, deque for queues)
3. Eliminate redundant work (cache repeated computations)
4. Remove dead code and unused imports
5. Apply language-specific best practices
6. Improve error handling and logging
7. Simplify complex conditional logic

If the code is already well-optimized, return: {"issues": []}"""

    def get_rag_queries(self) -> List[str]:
        return [
            "redundant computation repeated calculation",
            "unused variable import dead code",
            "manual loop instead of built-in function",
            "inefficient string building concatenation",
            "missing cache memoization repeated calls",
            "duplicate code copy paste violation",
            "poor variable naming unclear code",
            "missing error handling try except",
        ]

    def get_human_prompt(self, state: AgentReviewState) -> str:
        files_info = self._build_file_context(state)
        rag_context = state.get("rag_context", "No context available.")

        full_code = ""
        for filename, content in state.get("raw_file_contents", {}).items():
            language = state.get("language_map", {}).get(filename, "")
            full_code += f"\n\n### File: {filename} ({language})\n```{language.lower()}\n{content}\n```"

        return f"""Review the following code for optimization opportunities and quality improvements.

## Files Being Reviewed
{files_info}

## Relevant Code Context (from semantic search)
{rag_context}

## Full Source Code
{full_code}

Identify practical improvements prioritized by impact. Return ONLY the JSON object."""

    def parse_llm_response(
        self, response_text: str, state: AgentReviewState
    ) -> List[CodeIssue]:
        data = self._extract_json(response_text)

        if not data:
            return []

        if isinstance(data, dict):
            issues_raw = data.get("issues", [])
        elif isinstance(data, list):
            issues_raw = data
        else:
            return []

        issues: List[CodeIssue] = []
        for i, item in enumerate(issues_raw):
            if not isinstance(item, dict):
                continue

            improvement = item.get("estimated_improvement", "")
            base_desc = item.get("description", "")
            enriched_desc = (
                f"{base_desc}\n\nEstimated improvement: {improvement}"
                if improvement else base_desc
            )

            issues.append(
                CodeIssue(
                    issue_id=item.get("issue_id", f"OPT_{i+1:03d}"),
                    category="optimization",
                    severity=item.get("severity", "low"),
                    title=item.get("title", "Optimization opportunity"),
                    description=enriched_desc,
                    filename=item.get("filename", "unknown"),
                    line_start=int(item.get("line_start", 0)),
                    line_end=int(item.get("line_end", 0)),
                    code_snippet=item.get("code_snippet", ""),
                    suggestion=item.get("suggestion", ""),
                    confidence=float(item.get("confidence", 0.8)),
                )
            )

        return issues

    def _write_findings(self, state, findings, logs):
        return {**state, "optimization_findings": findings, "agent_logs": logs}