"""
Continuous-RAG LangGraph Workflow
Defines the multi-agent graph that routes queries to the appropriate specialist agent.

Architecture:
    ┌──────────┐
    │  Router  │ ← Classifies intent
    └────┬─────┘
         │
    ┌────┴────────────────────┐
    │         │               │
    ▼         ▼               ▼
┌────────┐ ┌───────────┐ ┌───────────────┐
│Retriever│ │Compliance │ │Change Analyzer│
└────┬───┘ └─────┬─────┘ └──────┬────────┘
     │           │               │
     └───────────┼───────────────┘
                 ▼
          ┌─────────────┐
          │ Synthesizer  │ ← Formats response, saves history
          └─────────────┘
"""
from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.router import router_node
from app.agents.retriever import retriever_node
from app.agents.compliance import compliance_node
from app.agents.change_analyzer import change_analyzer_node
from app.agents.synthesizer import synthesizer_node
from app.config import logger


def route_by_intent(state: AgentState) -> str:
    """
    Conditional edge function — routes to the correct agent based on intent.
    Called after the Router node.
    """
    intent = state.get("intent", "question")
    logger.info("Routing to: %s", intent)
    return intent


def build_agent_graph():
    """
    Build and compile the LangGraph multi-agent workflow.
    Returns the compiled graph (runnable).
    """
    graph = StateGraph(AgentState)

    # ── Add Nodes ──
    graph.add_node("router", router_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("change_analyzer", change_analyzer_node)
    graph.add_node("synthesizer", synthesizer_node)

    # ── Set Entry Point ──
    graph.set_entry_point("router")

    # ── Conditional Routing from Router ──
    graph.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "question": "retriever",
            "compliance": "compliance",
            "what_changed": "change_analyzer",
        }
    )

    # ── All specialist agents flow to Synthesizer ──
    graph.add_edge("retriever", "synthesizer")
    graph.add_edge("compliance", "synthesizer")
    graph.add_edge("change_analyzer", "synthesizer")

    # ── Synthesizer ends the workflow ──
    graph.add_edge("synthesizer", END)

    # ── Compile ──
    compiled = graph.compile()
    logger.info("LangGraph agent workflow compiled successfully")
    return compiled


# Build the graph once at module level (singleton)
agent_workflow = build_agent_graph()


def run_agent(query: str, chat_history: list[dict] = None) -> dict:
    """
    Run the full agent pipeline for a user query.
    chat_history: list of {role: "user"|"assistant", content: str} for context.
    """
    logger.info("=" * 50)
    logger.info("AGENT PIPELINE START: '%s'", query[:80])
    logger.info("=" * 50)

    initial_state: AgentState = {
        "query": query,
        "original_query": query,
        "chat_history": chat_history or [],
        "agent_trace": [],
    }

    # Run the graph
    final_state = agent_workflow.invoke(initial_state)

    logger.info("AGENT PIPELINE COMPLETE")
    logger.info("  Intent: %s", final_state.get("intent"))
    logger.info("  Confidence: %.1f%%", final_state.get("confidence", 0))
    logger.info("  Sources: %d", len(final_state.get("sources", [])))
    logger.info("  Trace steps: %d", len(final_state.get("agent_trace", [])))
    logger.info("=" * 50)

    return {
        "answer": final_state.get("final_answer", "No answer generated."),
        "intent": final_state.get("intent", "unknown"),
        "intent_reasoning": final_state.get("intent_reasoning", ""),
        "sources": final_state.get("sources", []),
        "confidence": final_state.get("confidence", 0.0),
        "query": query,
        # Compliance-specific fields
        "verdict": final_state.get("verdict"),
        "sub_questions": final_state.get("sub_questions"),
        "findings": final_state.get("findings"),
        "conflicts": final_state.get("conflicts"),
        "conditions": final_state.get("conditions"),
        # Change analysis fields
        "change_report": final_state.get("change_report"),
        # Observability
        "agent_trace": final_state.get("agent_trace", []),
    }
