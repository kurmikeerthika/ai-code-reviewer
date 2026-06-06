# app/agents/complexity_agent.py
# Analyzes time and space complexity of algorithms.

import logging
from typing import List
from app.agents.base_agent import BaseReviewAgent
from app.agents.state import AgentReviewState, CodeIssue

logger = logging.getLogger(__name__)


class ComplexityAgent(BaseReviewAgent):
    """
    Specialist agent focused on algorithmic complexity analysis.

    Detects:
    - O(n²) or worse nested loops
    - Repeated expensive computations inside loops
    - Inefficient data structure usage
    - Unnecessary recursion depth
    - Missing memoization / caching opportunities
    - Exponential complexity algorithms
    """

    AGENT_NAME = "ComplexityAnalyst"

    SYSTEM_PROMPT = """You are an algorithms expert specializing in computational complexity analysis.

Your task is to analyze the time and space complexity of functions and algorithms in the provided code.
Identify all cases where complexity could be significantly improved.

You MUST respond with ONLY valid JSON in this exact format:
{
  "issues": [
    {
      "issue_id": "CPX_001",
      "title": "Short title e.g. O(n²) nested loop in sort function",
      "description": "Current complexity explanation and why it matters",
      "current_complexity": "O(n²)",
      "optimal_complexity": "O(n log n)",
      "filename": "filename.py",
      "line_start": 15,
      "line_end": 22,
      "code_snippet": "the complex code",
      "suggestion": "How to improve — include better algorithm or data structure",
      "severity": "critical|high|medium|low|info",
      "confidence": 0.9
    }
  ]
}

Severity guide for complexity:
- critical: exponential O(2^n) or factorial O(n!)
- high: O(n²) or O(n³) on potentially large inputs
- medium: unnecessary O(n log n) where O(n) is possible
- low: minor inefficiency, small constant factor improvement
- info: already optimal but alternative approach exists

If all algorithms are optimal, return: {"issues": []}"""

    def get_rag_queries(self) -> List[str]:
        return [
            "nested for loop quadratic complexity",
            "repeated computation inside loop",
            "inefficient sorting algorithm bubble sort",
            "missing memoization dynamic programming",
            "linear search instead of hash lookup",
            "recursive function without base case optimization",
            "string concatenation in loop",
        ]

    def get_human_prompt(self, state: AgentReviewState) -> str:
        files_info = self._build_file_context(state)
        rag_context = state.get("rag_context", "No context available.")

        full_code = ""
        for filename, content in state.get("raw_file_contents", {}).items():
            language = state.get("language_map", {}).get(filename, "")
            full_code += f"\n\n### File: {filename} ({language})\n```{language.lower()}\n{content}\n```"

        return f"""Analyze the time and space complexity of all functions in the following code.

## Files Being Reviewed
{files_info}

## Relevant Code Context (from semantic search)
{rag_context}

## Full Source Code
{full_code}

For each function or algorithm with complexity issues, report the current and optimal Big-O.
Return ONLY the JSON object."""

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

            # Enrich description with complexity info
            current = item.get("current_complexity", "Unknown")
            optimal = item.get("optimal_complexity", "Unknown")
            base_desc = item.get("description", "")
            enriched_desc = (
                f"{base_desc}\n\n"
                f"Current complexity: {current} → Optimal: {optimal}"
            )

            issues.append(
                CodeIssue(
                    issue_id=item.get("issue_id", f"CPX_{i+1:03d}"),
                    category="complexity",
                    severity=item.get("severity", "medium"),
                    title=item.get("title", "Complexity issue"),
                    description=enriched_desc,
                    filename=item.get("filename", "unknown"),
                    line_start=int(item.get("line_start", 0)),
                    line_end=int(item.get("line_end", 0)),
                    code_snippet=item.get("code_snippet", ""),
                    suggestion=item.get("suggestion", ""),
                    confidence=float(item.get("confidence", 0.85)),
                )
            )

        return issues

    def _write_findings(self, state, findings, logs):
        return {**state, "complexity_findings": findings, "agent_logs": logs}