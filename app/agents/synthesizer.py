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

    # ── Clean GPT-OSS formatting artifacts ──
    import re
    if answer:
        # STEP 1: Normalize ALL unicode spaces → regular ASCII space
        answer = re.sub(r'[\u00a0\u202f\u2000-\u200b\u3000]+', ' ', answer)

        # STEP 2: Normalize ALL unicode dashes → ASCII hyphen '-'
        # (GPT-OSS uses \u2011 non-breaking hyphen, \u2013 en-dash, \u2014 em-dash)
        answer = re.sub(r'[\u2011\u2012\u2013\u2014\u2015\u2212]', '-', answer)

        # STEP 3: Smart bracket extractor for 【value - source】 patterns
        # GPT-OSS puts factual values inside 【...】 like 【16 days — HR_Policy.pdf】
        def _extract_bracket(m):
            inner = m.group(1).strip()
            # Case 1: Bracket contains a citation separator (—, -, ,) before a .pdf filename
            # e.g. '6 days — HR_Policy.pdf' or '16 days - HR_Policy.pdf, Page 1'
            match = re.search(r'^(.*?)\s*[\u2011-\u2015\u2212\-,;]\s*[A-Za-z0-9_\-]+\.pdf.*$', inner, flags=re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if val and not val.lower().endswith('.pdf'):
                    return val

            # Case 2: Bracket is a pure citation tag (e.g. 'HR_Policy.pdf', 'HR_Policy.pdf, Page 1')
            if re.match(r'^[A-Za-z0-9_\-]+\.pdf', inner, flags=re.IGNORECASE):
                return ''

            # Case 3: Bracket contains normal sentence text (e.g. 'Upload the updated HR_Policy.pdf')
            return inner

        answer = re.sub(r'\u3010(.*?)\u3011', _extract_bracket, answer)

        # STEP 4: Strip parenthetical PDF citations: (HR_Policy.pdf, Page 1, v1)
        answer = re.sub(r'\s*\([^)]{0,80}\.pdf[^)]*\)', '', answer)

        # STEP 5: Collapse multiple spaces and trim
        answer = re.sub(r'[ \t]{2,}', ' ', answer).strip()

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
