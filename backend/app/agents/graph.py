# app/agents/graph.py
# Defines the LangGraph multi-agent workflow.
#
# LangGraph works like this:
# - Each "node" is an async function that receives State and returns updated State
# - "Edges" define the order nodes run
# - StateGraph compiles everything into a runnable pipeline
#
# Our graph:
#   START
#     └─► orchestrate (fetch RAG context)
#           └─► bug_detection
#                 └─► security_analysis
#                       └─► complexity_analysis
#                             └─► optimization_analysis
#                                   └─► synthesize
#                                         └─► END

import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentReviewState
from app.agents.bug_detector import BugDetectorAgent
from app.agents.security_agent import SecurityAgent
from app.agents.complexity_agent import ComplexityAgent
from app.agents.optimizer_agent import OptimizerAgent
from app.agents.synthesizer import SynthesizerAgent
from app.rag.rag_pipeline import rag_pipeline

logger = logging.getLogger(__name__)

# Instantiate all agents (singletons — created once, reused)
bug_agent = BugDetectorAgent()
security_agent = SecurityAgent()
complexity_agent = ComplexityAgent()
optimizer_agent = OptimizerAgent()
synthesizer_agent = SynthesizerAgent()


# ---------------------------------------------------------------------------
# Node Functions
# Each function matches LangGraph's expected signature:
#   async def node_name(state: AgentReviewState) -> AgentReviewState
# ---------------------------------------------------------------------------

async def orchestrate_node(state: AgentReviewState) -> AgentReviewState:
    """
    First node: fetches relevant code context from ChromaDB
    and writes it into the state for all subsequent agents.
    """
    logger.info(f"[Orchestrator] Starting pipeline for session: {state['session_id']}")

    logs = list(state.get("agent_logs", []))
    logs.append("Orchestrator: fetching RAG context")

    # Combine all agents' search queries for a rich context fetch
    all_queries = (
        bug_agent.get_rag_queries()
        + security_agent.get_rag_queries()
        + complexity_agent.get_rag_queries()
        + optimizer_agent.get_rag_queries()
    )

    # Remove duplicate queries
    unique_queries = list(dict.fromkeys(all_queries))
    logger.info(f"[Orchestrator] Running {len(unique_queries)} RAG queries")

    # Fetch context from ChromaDB
    rag_context = await rag_pipeline.build_context_for_review(
        session_id=state["session_id"],
        review_queries=unique_queries[:15],  # Cap at 15 to avoid too many API calls
        top_k_per_query=2,
    )

    logs.append(
        f"Orchestrator: RAG context built "
        f"({len(rag_context)} chars)"
    )

    return {
        **state,
        "rag_context": rag_context,
        "status": "processing",
        "agent_logs": logs,
        # Initialize all finding lists to empty
        "bug_findings": [],
        "security_findings": [],
        "complexity_findings": [],
        "optimization_findings": [],
    }


async def bug_detection_node(state: AgentReviewState) -> AgentReviewState:
    """Node: runs the bug detector agent."""
    return await bug_agent.run(state)


async def security_analysis_node(state: AgentReviewState) -> AgentReviewState:
    """Node: runs the security analyst agent."""
    return await security_agent.run(state)


async def complexity_analysis_node(state: AgentReviewState) -> AgentReviewState:
    """Node: runs the complexity analyst agent."""
    return await complexity_agent.run(state)


async def optimization_node(state: AgentReviewState) -> AgentReviewState:
    """Node: runs the optimizer agent."""
    return await optimizer_agent.run(state)


async def synthesize_node(state: AgentReviewState) -> AgentReviewState:
    """Node: runs the synthesizer — combines all findings into the final report."""
    return await synthesizer_agent.run(state)


# ---------------------------------------------------------------------------
# Build and Compile the Graph
# ---------------------------------------------------------------------------

def build_review_graph() -> StateGraph:
    """
    Construct the LangGraph StateGraph and compile it into a runnable.

    The pipeline runs sequentially:
    orchestrate → bug → security → complexity → optimize → synthesize

    (Sequential rather than parallel because each agent builds on
    the shared state and OpenAI rate limits make parallel risky.)
    """
    # Create the graph with our state type
    graph = StateGraph(AgentReviewState)

    # Register all nodes
    graph.add_node("orchestrate", orchestrate_node)
    graph.add_node("bug_detection", bug_detection_node)
    graph.add_node("security_analysis", security_analysis_node)
    graph.add_node("complexity_analysis", complexity_analysis_node)
    graph.add_node("optimization", optimization_node)
    graph.add_node("synthesize", synthesize_node)

    # Define the edges (execution order)
    graph.add_edge(START, "orchestrate")
    graph.add_edge("orchestrate", "bug_detection")
    graph.add_edge("bug_detection", "security_analysis")
    graph.add_edge("security_analysis", "complexity_analysis")
    graph.add_edge("complexity_analysis", "optimization")
    graph.add_edge("optimization", "synthesize")
    graph.add_edge("synthesize", END)

    # Compile into a runnable
    compiled = graph.compile()
    logger.info("LangGraph review pipeline compiled successfully")
    return compiled


# Build once at import time — reused for every review request
review_graph = build_review_graph()


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------

async def run_review_pipeline(
    session_id: str,
    filenames: list,
    language_map: dict,
    file_contents: dict,
) -> Dict[str, Any]:
    """
    Main entry point called by the review API endpoint.

    Initializes the state and runs the full LangGraph pipeline.

    Args:
        session_id:    Upload session ID (used to fetch from ChromaDB)
        filenames:     List of filenames being reviewed
        language_map:  Dict of filename → language
        file_contents: Dict of filename → full code string

    Returns:
        The final_report dict from the synthesizer
    """
    logger.info(f"Starting review pipeline: session={session_id}, files={filenames}")

    # Build the initial state
    initial_state: AgentReviewState = {
        "session_id": session_id,
        "filenames": filenames,
        "language_map": language_map,
        "raw_file_contents": file_contents,
        "rag_context": "",
        "bug_findings": [],
        "security_findings": [],
        "complexity_findings": [],
        "optimization_findings": [],
        "final_report": {},
        "review_summary": "",
        "total_issues": 0,
        "severity_counts": {},
        "status": "pending",
        "error_message": None,
        "agent_logs": [],
    }

    # Run the compiled graph
    final_state = await review_graph.ainvoke(initial_state)

    logger.info(
        f"Pipeline complete: session={session_id}, "
        f"status={final_state.get('status')}, "
        f"issues={final_state.get('total_issues')}"
    )

    return final_state.get("final_report", {})