"""
Synthesizer Agent
Final agent in the pipeline — formats the response, adds metadata, and saves to query history.
This is the last node before the response is returned to the user.
"""
from app.config import logger
from app import database as db
from app.agents.state import AgentState


def synthesizer_node(state: AgentState) -> AgentState:
    """
    Final synthesis step:
    1. Ensure all fields are populated
    2. Log the query to history
    3. Add final trace entry
    """
    trace = state.get("agent_trace", [])
    trace.append("SYNTHESIZER: Preparing final response...")

    intent = state.get("intent", "question")
    query = state.get("query", "")
    answer = state.get("final_answer", "No answer generated.")
    sources = state.get("sources", [])
    confidence = state.get("confidence", 0.0)

    # Add intent-specific metadata to the answer
    intent_labels = {
        "question": "📋 Document Q&A",
        "compliance": "✅ Compliance Check",
        "what_changed": "📊 Change Analysis",
    }
    intent_label = intent_labels.get(intent, "Unknown")

    # Save to query history
    try:
        db.insert_query_history(
            query=query,
            answer=answer,
            intent=intent,
            sources=sources,
            confidence=confidence,
        )
        trace.append("SYNTHESIZER: Saved to query history")
    except Exception as e:
        logger.error("Failed to save query history: %s", e)
        trace.append(f"SYNTHESIZER: History save failed - {str(e)[:50]}")

    trace.append(f"SYNTHESIZER: Done — intent={intent}, confidence={confidence:.1f}%, sources={len(sources)}")

    return {
        **state,
        "final_answer": answer,
        "sources": sources,
        "confidence": confidence,
        "agent_trace": trace,
    }
