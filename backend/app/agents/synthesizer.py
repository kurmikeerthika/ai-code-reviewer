# app/agents/synthesizer.py
# Combines all agent findings into a single structured report.

import logging
from datetime import datetime
from typing import List, Dict, Any
# from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import AgentReviewState, CodeIssue
from app.core.config import settings

logger = logging.getLogger(__name__)


class SynthesizerAgent:
    """
    Final agent in the pipeline. Reads all findings and produces:
    1. A structured JSON report combining all issues
    2. A human-readable summary paragraph
    3. Severity counts and statistics
    """

    AGENT_NAME = "Synthesizer"

    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0
        )

    def _count_severities(self, all_issues: List[CodeIssue]) -> Dict[str, int]:
        """Count issues by severity level."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for issue in all_issues:
            severity = issue.get("severity", "info").lower()
            if severity in counts:
                counts[severity] += 1
        return counts

    def _issues_to_dict_list(self, issues: List[CodeIssue]) -> List[Dict]:
        """Convert CodeIssue TypedDicts to plain dicts for JSON serialization."""
        return [dict(issue) for issue in issues]

    async def _generate_summary(
        self, all_issues: List[CodeIssue], state: AgentReviewState
    ) -> str:
        """Ask the LLM to write a human-readable review summary."""
        filenames = ", ".join(state.get("filenames", []))
        total = len(all_issues)
        severity_counts = self._count_severities(all_issues)

        issues_text = "\n".join([
            f"- [{i['severity'].upper()}] {i['category']}: {i['title']}"
            for i in all_issues[:20]  # Cap at 20 for prompt length
        ])

        system = SystemMessage(content=(
            "You are a senior engineering lead writing a code review summary. "
            "Be concise, constructive, and specific. 3-5 sentences maximum."
        ))
        human = HumanMessage(content=f"""Write a professional code review summary for these files: {filenames}

Total issues found: {total}
Severity breakdown: {severity_counts}

Issues:
{issues_text}

Write a 3-5 sentence summary covering: overall code health, most critical concerns, and top priorities for the developer.""")

        try:
            response = await self.llm.ainvoke([system, human])
            return response.content.strip()
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return (
                f"Code review completed. Found {total} issue(s) across "
                f"{len(state.get('filenames', []))} file(s). "
                f"Critical: {severity_counts['critical']}, "
                f"High: {severity_counts['high']}, "
                f"Medium: {severity_counts['medium']}."
            )

    async def run(self, state: AgentReviewState) -> AgentReviewState:
        """
        Combine all agent findings into the final report.
        This is the last node in the LangGraph pipeline.
        """
        logger.info(f"[{self.AGENT_NAME}] Synthesizing all findings...")

        logs = list(state.get("agent_logs", []))
        logs.append(f"{self.AGENT_NAME}: started")
        
        all_issues: List[CodeIssue] = (
            list(state.get("bug_findings", []))
            + list(state.get("security_findings", []))
            + list(state.get("complexity_findings", []))
            + list(state.get("optimization_findings", []))
        )

        # Collect all findings from all agents
        all_issues: List[CodeIssue] = (
            list(state.get("bug_findings", []))
            + list(state.get("security_findings", []))
            + list(state.get("complexity_findings", []))
            + list(state.get("optimization_findings", []))
        )

        total_issues = len(all_issues)
        severity_counts = self._count_severities(all_issues)

        # Generate human-readable summary
        summary = await self._generate_summary(all_issues, state)

        # Build the complete structured report
        final_report: Dict[str, Any] = {
            "report_id": f"review_{state['session_id']}",
            "session_id": state["session_id"],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "files_reviewed": state.get("filenames", []),
            "languages": list(set(state.get("language_map", {}).values())),
            "summary": summary,
            "statistics": {
                "total_issues": total_issues,
                "severity_counts": severity_counts,
                "by_category": {
                    "bugs": len(state.get("bug_findings", [])),
                    "security": len(state.get("security_findings", [])),
                    "complexity": len(state.get("complexity_findings", [])),
                    "optimization": len(state.get("optimization_findings", [])),
                },
            },
            "issues": self._issues_to_dict_list(all_issues),
            "agent_logs": logs,
        }

        logs.append(
            f"{self.AGENT_NAME}: completed — "
            f"{total_issues} total issues synthesized"
        )

        logger.info(
            f"[{self.AGENT_NAME}] Report complete: "
            f"{total_issues} issues — {severity_counts}"
        )

        return {
            **state,
            "final_report": final_report,
            "review_summary": summary,
            "total_issues": total_issues,
            "severity_counts": severity_counts,
            "status": "completed",
            "agent_logs": logs,
        }
        
 