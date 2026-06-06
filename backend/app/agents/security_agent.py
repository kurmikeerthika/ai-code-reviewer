# app/agents/security_agent.py
# Detects security vulnerabilities: injection, auth issues, secrets, etc.

import logging
from typing import List
from app.agents.base_agent import BaseReviewAgent
from app.agents.state import AgentReviewState, CodeIssue

logger = logging.getLogger(__name__)


class SecurityAgent(BaseReviewAgent):
    """
    Specialist agent focused on security vulnerability detection.

    Detects:
    - SQL injection
    - Command injection
    - Hardcoded secrets/passwords/API keys
    - Insecure cryptography (MD5, SHA1, weak keys)
    - Missing authentication/authorization
    - Path traversal vulnerabilities
    - XSS (Cross-Site Scripting)
    - CSRF vulnerabilities
    - Insecure deserialization
    - Sensitive data exposure
    """

    AGENT_NAME = "SecurityAnalyst"

    SYSTEM_PROMPT = """You are a senior application security engineer and penetration tester.

Your task is to identify ALL security vulnerabilities in the provided source code.
Reference OWASP Top 10 categories where applicable.

You MUST respond with ONLY valid JSON in this exact format:
{
  "issues": [
    {
      "issue_id": "SEC_001",
      "title": "Short vulnerability title",
      "description": "What the vulnerability is, how it can be exploited, and its impact",
      "owasp_category": "A03:2021 - Injection",
      "filename": "filename.py",
      "line_start": 5,
      "line_end": 7,
      "code_snippet": "the vulnerable code",
      "suggestion": "Secure alternative code or fix description",
      "severity": "critical|high|medium|low|info",
      "confidence": 0.9
    }
  ]
}

OWASP Top 10 categories to check:
A01 - Broken Access Control
A02 - Cryptographic Failures
A03 - Injection (SQL, Command, LDAP)
A04 - Insecure Design
A05 - Security Misconfiguration
A06 - Vulnerable Components
A07 - Authentication Failures
A08 - Integrity Failures
A09 - Logging Failures
A10 - SSRF

If no vulnerabilities are found, return: {"issues": []}"""

    def get_rag_queries(self) -> List[str]:
        return [
            "SQL injection string concatenation query",
            "hardcoded password secret api key token",
            "command injection shell execute subprocess",
            "MD5 SHA1 weak cryptography hash",
            "missing authentication authorization check",
            "path traversal directory file access",
            "eval exec dangerous function call",
            "sensitive data exposure logging",
        ]

    def get_human_prompt(self, state: AgentReviewState) -> str:
        files_info = self._build_file_context(state)
        rag_context = state.get("rag_context", "No context available.")

        full_code = ""
        for filename, content in state.get("raw_file_contents", {}).items():
            language = state.get("language_map", {}).get(filename, "")
            full_code += f"\n\n### File: {filename} ({language})\n```{language.lower()}\n{content}\n```"

        return f"""Perform a comprehensive security audit of the following code.

## Files Being Reviewed
{files_info}

## Relevant Code Context (from semantic search)
{rag_context}

## Full Source Code
{full_code}

Identify ALL security vulnerabilities. Return ONLY the JSON object."""

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
            issues.append(
                CodeIssue(
                    issue_id=item.get("issue_id", f"SEC_{i+1:03d}"),
                    category="security",
                    severity=item.get("severity", "high"),
                    title=item.get("title", "Security vulnerability"),
                    description=item.get("description", ""),
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
        return {**state, "security_findings": findings, "agent_logs": logs}