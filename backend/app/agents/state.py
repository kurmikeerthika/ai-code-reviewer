# app/agents/state.py
# Defines the shared state object that flows through the LangGraph pipeline.
#
# Think of State as a shared notepad:
# - The orchestrator writes the code context onto it
# - Each agent reads the code and writes its findings
# - The synthesizer reads all findings and writes the final report
# - LangGraph manages passing this state between nodes automatically

from typing import TypedDict, List, Optional, Dict, Any
from app.models.schemas import SeverityLevel, IssueCategory


class CodeIssue(TypedDict):
    """
    Represents a single issue found by any agent.
    All agents produce lists of these.
    """
    issue_id: str           # Unique ID e.g. "BUG_001"
    category: str           # From IssueCategory enum
    severity: str           # From SeverityLevel enum
    title: str              # Short summary e.g. "Division by zero"
    description: str        # Full explanation of the issue
    filename: str           # Which file has the issue
    line_start: int         # Starting line (0 if unknown)
    line_end: int           # Ending line (0 if unknown)
    code_snippet: str       # The problematic code
    suggestion: str         # How to fix it
    confidence: float       # Agent's confidence 0.0–1.0


class AgentReviewState(TypedDict):
    """
    The shared state object passed between all LangGraph nodes.

    Each field is written by one stage and read by later stages:

    Stage 1 (Orchestrator):
        session_id, filenames, language_map, rag_context, raw_file_contents

    Stage 2 (Specialist Agents — run in parallel conceptually):
        bug_findings, security_findings, complexity_findings, optimization_findings

    Stage 3 (Synthesizer):
        final_report, review_summary, total_issues, severity_counts

    Metadata:
        status, error_message, agent_logs
    """

    # --- Input ---
    session_id: str
    filenames: List[str]
    language_map: Dict[str, str]        # filename → language
    raw_file_contents: Dict[str, str]   # filename → full code string
    rag_context: str                    # Retrieved chunks formatted for LLM

    # --- Agent Findings ---
    bug_findings: List[CodeIssue]
    security_findings: List[CodeIssue]
    complexity_findings: List[CodeIssue]
    optimization_findings: List[CodeIssue]

    # --- Final Output ---
    final_report: Dict[str, Any]        # Complete structured report
    review_summary: str                 # One-paragraph human summary
    total_issues: int
    severity_counts: Dict[str, int]     # {"critical": 1, "high": 2, ...}

    # --- Pipeline Metadata ---
    status: str                         # "running" | "completed" | "failed"
    error_message: Optional[str]
    agent_logs: List[str]               # Debug log from each agent