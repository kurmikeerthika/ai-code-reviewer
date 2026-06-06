# app/agents/bug_detector.py
# Detects bugs, logic errors, and runtime exceptions in code.

import logging
from typing import List
from app.agents.base_agent import BaseReviewAgent
from app.agents.state import AgentReviewState, CodeIssue

logger = logging.getLogger(__name__)


class BugDetectorAgent(BaseReviewAgent):
    """
    Specialist agent focused on finding bugs and logic errors.

    Detects:
    - Division by zero
    - Null/None dereferences
    - Off-by-one errors
    - Infinite loops
    - Uncaught exceptions
    - Wrong data type assumptions
    - Resource leaks (files/connections not closed)
    """

    AGENT_NAME = "BugDetector"

    SYSTEM_PROMPT = """You are an expert software engineer specializing in bug detection and code correctness.

Your task is to analyze the provided source code and identify ALL bugs, logic errors, and potential runtime exceptions.

You MUST respond with ONLY valid JSON in this exact format — no explanation, no markdown, just JSON:
{
  "issues": [
    {
      "issue_id": "BUG_001",
      "title": "Short descriptive title",
      "description": "Detailed explanation of why this is a bug and when it would occur",
      "filename": "filename.py",
      "line_start": 10,
      "line_end": 12,
      "code_snippet": "the problematic code here",
      "suggestion": "Exact corrected code or fix description",
      "severity": "critical|high|medium|low|info",
      "confidence": 0.95
    }
  ]
}

Severity guide:
- critical: causes crashes or data corruption
- high: significant malfunction under common conditions
- medium: malfunction under edge cases
- low: minor incorrect behavior
- info: code smell or potential future issue
Even if code generally works, identify:
- risky patterns
- edge cases
- maintainability concerns
- weak validation
- poor error handling
- suspicious logic

Prefer returning low-severity improvements instead of zero issues.

If absolutely no concerns exist, return:
{"issues": []}"""

    def get_rag_queries(self) -> List[str]:
        return [
            "division by zero error",
            "null pointer none dereference",
            "uncaught exception error handling",
            "infinite loop condition",
            "off by one index error",
            "resource leak file connection not closed",
            "type error wrong data type",
        ]

    def get_human_prompt(self, state: AgentReviewState) -> str:
        files_info = self._build_file_context(state)
        rag_context = state.get("rag_context", "No context available.")

        # Build the full code listing so the LLM sees everything
        full_code = ""
        MAX_FILE_LENGTH = 4000
        for filename, content in state.get("raw_file_contents", {}).items():
            language = state.get("language_map", {}).get(filename, "")
            trimmed_content = content[:MAX_FILE_LENGTH]

            full_code += (
                f"\n\n### File: {filename} ({language})"
                f"\n```{language.lower()}\n{trimmed_content}\n```"
                )
        return f"""Please analyze the following code for bugs and logic errors.

## Files Being Reviewed
{files_info}

## Relevant Code Context (from semantic search)
{rag_context}

## Full Source Code
{full_code}

Identify ALL bugs. Return ONLY the JSON object described in your instructions."""

    def parse_llm_response(
        self, response_text: str, state: AgentReviewState
    ) -> List[CodeIssue]:
        """Parse the JSON response into CodeIssue objects."""
        data = self._extract_json(response_text)
        
        print("\n=== BUG DETECTOR JSON ===")
        print(data)
        print("=========================\n")

        if not data:
            return []

        # Handle both {"issues": [...]} and plain [...]
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
            issues.append(
                CodeIssue(
                    issue_id=item.get("issue_id", f"BUG_{i+1:03d}"),
                    category="bug",
                    severity=item.get("severity", "medium"),
                    title=item.get("title", "Unknown bug"),
                    description=item.get("description", ""),
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
        return {**state, "bug_findings": findings, "agent_logs": logs}