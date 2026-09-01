"""
Router Agent
Classifies user intent to route to the correct specialist agent.
Uses LLM to understand whether the query is:
  - A simple question (→ Retriever)
  - A compliance check (→ Compliance Agent)
  - A change analysis request (→ Change Analyzer)
"""
import json
from app.config import groq_client, MODEL, logger
from app.agents.state import AgentState


ROUTER_PROMPT = """You are an intent classifier for an enterprise policy Q&A system. You MUST classify accurately.

RULES — read carefully:

1. "question" — User asks a FACTUAL question seeking specific information from documents.
   Key signals: "what is", "how many", "how much", "list the", "tell me about", "what does the policy say"
   Examples:
   - "What is the leave policy?" → question
   - "How many sick days do I get?" → question
   - "What is the home office setup allowance?" → question
   - "What are the office hours?" → question
   - "What equipment do employees receive?" → question

2. "compliance" — User asks if something is ALLOWED or PERMITTED, or asks "can I", "am I allowed", "is it okay".
   Key signals: "can I", "am I allowed", "is it permitted", "is it okay to", "may I", working from specific locations
   Examples:
   - "Can I work from home 3 days a week?" → compliance
   - "Am I allowed to use ChatGPT at work?" → compliance
   - "Can I work remotely from Dubai for 2 months?" → compliance
   - "Is it okay to expense a co-working space?" → compliance
   - "Can I use personal devices for work?" → compliance
   - "Am I allowed to use ChatGPT for my work tasks?" → compliance

3. "what_changed" — User asks about CHANGES, UPDATES, or DIFFERENCES between document versions.
   Key signals: "what changed", "what's new", "what's different", "updates", "modifications"
   Examples:
   - "What changed in the HR policy?" → what_changed
   - "What's new in the latest update?" → what_changed

IMPORTANT: If the query contains "can I", "am I allowed", "is it permitted", "is it okay" — ALWAYS classify as "compliance", even if it seems like a simple question.

Respond ONLY with valid JSON:
{
  "intent": "question" | "compliance" | "what_changed",
  "reasoning": "Brief explanation"
}

User query: """


REWRITE_PROMPT = """You are a query rewriter. Given a conversation history and a new user message, rewrite the message as a complete standalone question.

If the message is already a clear standalone question, return it as-is.
If it's a vague follow-up (like "2 days?", "what about that?", "how?"), rewrite it using context from the history.

Conversation history:
{history}

New message: {query}

Respond with ONLY the rewritten question, nothing else."""


def rewrite_query_if_needed(query: str, chat_history: list[dict]) -> str:
    """
    Fix Issue #2: Rewrite vague follow-up queries using conversation history.
    E.g., "2days?" after asking about WFH → "Can I work from home 2 days a week?"
    """
    # If query is clear enough (>30 chars, has a verb), skip rewriting
    if len(query) > 30 and any(w in query.lower() for w in ['what', 'how', 'can', 'is', 'are', 'do', 'does', 'where', 'when']):
        return query

    # If no history, can't rewrite
    if not chat_history:
        return query

    # Build history string (last 4 messages)
    recent = chat_history[-4:]
    history_str = "\n".join([f"{m['role'].upper()}: {m['content'][:200]}" for m in recent])

    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": REWRITE_PROMPT.format(history=history_str, query=query)}],
            temperature=0.0,
            max_tokens=150,
        )
        rewritten = response.choices[0].message.content.strip()
        if rewritten and len(rewritten) > 5:
            logger.info("Query rewritten: '%s' → '%s'", query, rewritten)
            return rewritten
    except Exception as e:
        logger.error("Query rewrite failed: %s", e)

    return query


def router_node(state: AgentState) -> AgentState:
    """
    Classify user intent and route to the appropriate agent.
    First rewrites vague queries using chat history, then classifies intent.
    """
    original_query = state["query"]
    chat_history = state.get("chat_history", [])
    trace = state.get("agent_trace", [])

    # Step 1: Rewrite vague queries using conversation context
    query = rewrite_query_if_needed(original_query, chat_history)
    if query != original_query:
        trace.append(f"ROUTER: Rewrote query: '{original_query}' → '{query}'")

    trace.append("ROUTER: Classifying intent...")

    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": ROUTER_PROMPT + query}],
            temperature=0.0,
            max_tokens=150,
        )

        raw = response.choices[0].message.content.strip()

        # Normalize unicode chars GPT-OSS injects that break json.loads()
        import re
        raw = re.sub(r'[\u00a0\u202f\u2000-\u200b]+', ' ', raw)  # non-breaking spaces
        raw = re.sub(r'[\u2011\u2012\u2013\u2014\u2015]', '-', raw)  # unicode dashes

        # Parse JSON response — handle markdown code blocks
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        # Extract JSON object if buried in prose
        json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

        result = json.loads(raw)
        intent = result.get("intent", "question")
        reasoning = result.get("reasoning", "")

        # Validate intent
        valid_intents = {"question", "compliance", "what_changed"}
        if intent not in valid_intents:
            intent = "question"
            reasoning = "Defaulting to question (invalid intent returned)"

    except Exception as e:
        logger.error("Router failed, defaulting to 'question': %s", e)
        intent = "question"
        reasoning = f"Default (router error: {str(e)[:50]})"

    trace.append(f"ROUTER: Intent = '{intent}' | Reason: {reasoning}")
    logger.info("Router → intent='%s', reasoning='%s'", intent, reasoning)

    return {
        **state,
        "intent": intent,
        "intent_reasoning": reasoning,
        "agent_trace": trace,
    }
