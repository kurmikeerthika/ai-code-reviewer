# app/agents/base_agent.py
# Abstract base class for all AI review agents.
#
# Each specialist agent inherits from this class and only needs to define:
#   1. SYSTEM_PROMPT  — the agent's persona and instructions
#   2. get_queries()  — what to search for in ChromaDB
#   3. parse_response() — how to parse the LLM's JSON output
#
# The base class handles:
#   - Building the LLM prompt with RAG context
#   - Calling OpenAI
#   - JSON extraction from the response
#   - Error handling and fallbacks
from langchain_groq import ChatGroq
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Any

#from langchain_community.chat_models import ChatOllama
 
# from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import AgentReviewState, CodeIssue
from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseReviewAgent(ABC):
    """
    Abstract base class for all code review agents.
    Subclasses implement the abstract methods to specialize behavior.
    """

    # Override these in each subclass
    AGENT_NAME: str = "BaseAgent"
    SYSTEM_PROMPT: str = "You are a code review assistant."
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0,
            model_kwargs={
                "response_format": {"type": "json_object"}
            }
        )

    @abstractmethod
    def get_rag_queries(self) -> List[str]:
        """
        Return a list of search queries to fetch relevant code chunks
        from ChromaDB before running this agent's analysis.

        Example:
            return [
                "SQL injection vulnerability",
                "unvalidated user input",
                "database query concatenation",
            ]
        """
        pass

    @abstractmethod
    def get_human_prompt(self, state: AgentReviewState) -> str:
        """
        Build the human-turn prompt for this agent using the current state.
        The prompt should instruct the LLM to return JSON.
        """
        pass

    @abstractmethod
    def parse_llm_response(self, response_text: str, state: AgentReviewState) -> List[CodeIssue]:
        """
        Parse the LLM's text response into a list of CodeIssue objects.
        """
        pass

    def _extract_json(self, text: str) -> Any:
        """
        Robustly extract JSON from LLM response text.

        LLMs sometimes wrap JSON in markdown code blocks like:
```json
            { ... }
```
        This method handles all common formats.
        """
        # Try 1: Strip markdown code fences and parse directly
        cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try 2: Find the first { ... } or [ ... ] block
        patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Object
            r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # Array
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        # Try 3: Find anything between first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        # Try 4: Find anything between first [ and last ]
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        logger.error(f"[{self.AGENT_NAME}] Could not extract JSON from response")
        return []

    def _build_file_context(self, state: AgentReviewState) -> str:
        """
        Build a concise file listing for the prompt so the LLM
        knows what files are being reviewed.
        """
        lines = []
        for filename, language in state.get("language_map", {}).items():
            content = state.get("raw_file_contents", {}).get(filename, "")
            line_count = content.count("\n") + 1
            lines.append(f"  - {filename} ({language}, {line_count} lines)")
        return "\n".join(lines) if lines else "  - No files"

    async def run(self, state: AgentReviewState) -> AgentReviewState:
        """
        Execute this agent:
        1. Log start
        2. Build prompt (system + human)
        3. Call OpenAI
        4. Parse response into CodeIssue list
        5. Write findings into state
        6. Return updated state

        This method is called by LangGraph as a node function.
        """
        logger.info(f"[{self.AGENT_NAME}] Starting analysis for session: {state['session_id']}")

        # Add to agent log
        logs = list(state.get("agent_logs", []))
        logs.append(f"{self.AGENT_NAME}: started")

        try:
            # Build the messages for the LLM
            system_msg = SystemMessage(content=self.SYSTEM_PROMPT)
            human_msg = HumanMessage(content=self.get_human_prompt(state))

            # Call OpenAI
            logger.info(f"[{self.AGENT_NAME}] Calling Groq {settings.groq_model}...")
            response = await self.llm.ainvoke([system_msg, human_msg])
            response_text = response.content
            
            print("\n\n========== RAW LLM RESPONSE ==========")
            print(response_text)
            print("======================================\n\n")

            logger.debug(f"[{self.AGENT_NAME}] Raw response (first 300 chars): {response_text[:300]}")

            # Parse into CodeIssue list
            findings = self.parse_llm_response(response_text, state)

            logger.info(f"[{self.AGENT_NAME}] Found {len(findings)} issue(s)")
            logs.append(f"{self.AGENT_NAME}: completed — {len(findings)} issue(s) found")

            # Write findings into state and return
            return self._write_findings(state, findings, logs)

        except Exception as e:
            error_msg = f"{self.AGENT_NAME} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            logs.append(error_msg)

            # Return state unchanged (with empty findings for this agent)
            return self._write_findings(state, [], logs)

    def _write_findings(
        self,
        state: AgentReviewState,
        findings: List[CodeIssue],
        logs: List[str],
    ) -> AgentReviewState:
        """
        Write this agent's findings into the correct state field.
        Subclasses may override this if needed.
        """
        # Default: subclasses override to set the right state key
        return {**state, "agent_logs": logs}
