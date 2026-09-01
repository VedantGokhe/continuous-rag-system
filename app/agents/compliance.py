"""
Compliance Checker Agent
Performs multi-document reasoning to verify if an action/request complies with company policies.

Flow:
1. Decompose the query into sub-questions targeting different policy areas
2. Retrieve relevant chunks for each sub-question (multi-query retrieval)
3. Cross-document reasoning to find conflicts and compile findings
4. Return a structured verdict: ALLOWED / DENIED / CONDITIONAL
"""
import json
import re
from app.config import groq_client, MODEL, logger
from app.retrieval import retrieve_multi_query
from app.agents.state import AgentState


def _clean_json(raw: str) -> str:
    """Extract clean JSON from LLM response (handles markdown blocks, thinking, etc.)."""
    text = raw.strip()
    # Normalize non-breaking hyphens and dashes (GPT-OSS uses \u2011 which breaks JSON)
    text = text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-')
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break
    # Find JSON object if buried in text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group(0)
    return text


DECOMPOSE_PROMPT = """You are a compliance analysis assistant for an enterprise policy system.

The user wants to check if something is allowed under company policies.

Break this query into 2-4 specific sub-questions that target different policy areas.
Each sub-question should search for a specific aspect of the compliance check.

User query: "{query}"

Respond ONLY with valid JSON:
{{
  "sub_questions": [
    "specific question about one policy area",
    "specific question about another policy area"
  ]}}"""


REASONING_PROMPT = """You are a compliance analysis expert. Follow this EXACT decision process step by step:

═══ STEP 1: CHECK FOR HARD PROHIBITIONS FIRST ═══
Scan ALL policy excerpts for ANY of these:
  - A tool/service listed as "PROHIBITED" (e.g., "ChatGPT — PROHIBITED")
  - A country/location listed as "Tier 3", "Not approved", or "NOT permitted"
  - An action described as "strictly forbidden" or "not allowed under any circumstances"

⚠️ If you find ANY hard prohibition that applies to the request → verdict MUST be "DENIED".
   Do NOT consider conditions, approvals, or workarounds. DENIED is final.
   Even if other policies mention conditions like VP approval — those do NOT override a prohibition.

═══ STEP 2: ONLY IF NO PROHIBITION FOUND, check these verdicts ═══
  - "ALLOWED" — The request is clearly within ALL policy limits, no issues.
  - "CONDITIONAL" — The request is possible but has requirements to meet, or policies conflict.
    * Requirements like "use VPN", "get manager approval" are CONDITIONS, not reasons to deny.
    * If a request is within stated limits (e.g., "2 remote days" when policy allows "max 2 days"), use ALLOWED or CONDITIONAL.
    * If two policies conflict, give CONDITIONAL and explain.

User's Request: "{query}"

Policy Excerpts Found:
{context}

Respond ONLY with valid JSON:
{{
  "findings": [
    {{
      "source": "document name and page",
      "finding": "what this document says about the request",
      "supports_request": true
    }}
  ],
  "conflicts": [
    {{
      "doc1": "first conflicting document",
      "doc2": "second conflicting document",
      "description": "what the conflict is about"
    }}
  ],
  "verdict": "ALLOWED",
  "conditions": ["list of conditions/requirements if CONDITIONAL"],
  "reasoning": "Brief overall explanation of the verdict"
}}"""


def compliance_node(state: AgentState) -> AgentState:
    """
    Multi-document compliance checking using Groq LLM.

    Steps:
    1. Decompose query into sub-questions
    2. Multi-query retrieval across documents
    3. Cross-document reasoning via LLM
    4. Return structured verdict
    """
    query = state["query"]
    trace = state.get("agent_trace", [])
    trace.append("COMPLIANCE: Starting multi-document compliance check...")

    # ── Step 1: Decompose into sub-questions ──
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": DECOMPOSE_PROMPT.format(query=query)
            }],
            temperature=0.1,
            max_tokens=400,
        )
        raw = _clean_json(response.choices[0].message.content.strip())
        decomposed = json.loads(raw)
        raw_sqs = decomposed.get("sub_questions", [query])

        # Sanitize: LLM sometimes returns dicts instead of strings
        sub_questions = []
        for sq in raw_sqs:
            if isinstance(sq, str):
                sub_questions.append(sq)
            elif isinstance(sq, dict):
                sub_questions.append(
                    sq.get("question", sq.get("sub_question", sq.get("text", str(sq))))
                )
            else:
                sub_questions.append(str(sq))

        if not sub_questions:
            sub_questions = [query]

    except Exception as e:
        logger.error("Decomposition failed: %s", e)
        sub_questions = [query]  # Fallback: use original query

    trace.append(f"COMPLIANCE: Decomposed into {len(sub_questions)} sub-questions")
    for i, sq in enumerate(sub_questions):
        trace.append(f"  Sub-Q{i+1}: {sq}")

    # ── Step 2: Multi-query retrieval ──
    all_chunks = retrieve_multi_query(sub_questions, top_k=3)
    trace.append(f"COMPLIANCE: Retrieved {len(all_chunks)} unique chunks across all sub-questions")

    if not all_chunks:
        return {
            **state,
            "sub_questions": sub_questions,
            "findings": [],
            "conflicts": [],
            "verdict": "UNKNOWN",
            "conditions": [],
            "final_answer": "No relevant policy documents found to assess compliance. Please upload relevant policy documents.",
            "sources": [],
            "confidence": 0.0,
            "agent_trace": trace,
        }

    # ── Step 3: Cross-document reasoning ──
    context_parts = []
    for c in all_chunks:
        header = f"[{c['filename']}, Page {c['page_num']}, v{c['version']}]"
        context_parts.append(f"{header}\n{c['text']}")

    context_text = "\n\n---\n\n".join(context_parts)

    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": REASONING_PROMPT.format(query=query, context=context_text)
            }],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = _clean_json(response.choices[0].message.content.strip())

        try:
            analysis = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed, attempting recovery from: %s", raw[:200])
            verdict_match = re.search(r'"verdict"\s*:\s*"(ALLOWED|DENIED|CONDITIONAL)"', raw)
            reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', raw)
            analysis = {
                "verdict": verdict_match.group(1) if verdict_match else "UNKNOWN",
                "reasoning": reasoning_match.group(1) if reasoning_match else "Analysis completed but response format was invalid. Please try again.",
                "findings": [],
                "conflicts": [],
                "conditions": [],
            }
            trace.append("COMPLIANCE: Recovered from malformed JSON")

        findings = analysis.get("findings", [])
        conflicts = analysis.get("conflicts", [])
        verdict = analysis.get("verdict", "UNKNOWN")
        conditions = analysis.get("conditions", [])
        reasoning = analysis.get("reasoning", "")

    except Exception as e:
        logger.error("Compliance reasoning failed: %s", e)
        findings = []
        conflicts = []
        verdict = "ERROR"
        conditions = []
        reasoning = f"Analysis error: {str(e)}"
        trace.append(f"COMPLIANCE: Reasoning error - {str(e)[:80]}")

    # ── Post-check: Override CONDITIONAL → DENIED if hard prohibitions found ──
    if verdict == "CONDITIONAL":
        prohibition_keywords = [
            "not permitted", "not approved", "tier 3", "prohibited",
            "strictly forbidden", "not allowed under any circumstances",
        ]
        context_lower = context_text.lower()

        found_prohibition = None
        for kw in prohibition_keywords:
            if kw in context_lower:
                found_prohibition = kw
                break

        if found_prohibition:
            unsupporting = [f for f in findings if not f.get("supports_request", True)]
            supporting = [f for f in findings if f.get("supports_request", True)]
            if len(unsupporting) > len(supporting):
                old_verdict = verdict
                verdict = "DENIED"
                reasoning = f"Hard prohibition detected in policy: '{found_prohibition}'. {reasoning}"
                conditions = []
                trace.append(f"COMPLIANCE: POST-CHECK override {old_verdict} → DENIED (found '{found_prohibition}')")
                logger.info("Compliance post-check: overrode %s → DENIED (keyword: '%s')", old_verdict, found_prohibition)

    trace.append(f"COMPLIANCE: Verdict = {verdict}")
    trace.append(f"COMPLIANCE: {len(findings)} findings, {len(conflicts)} conflicts")

    # Build clean chat answer
    final_answer = f"{reasoning}"

    if conditions:
        final_answer += "\n\n**Conditions:**"
        for cond in conditions:
            final_answer += f"\n- {cond}"

    # Build sources
    sources = [
        {
            "filename": c["filename"],
            "page_num": c["page_num"],
            "version": c["version"],
            "confidence": c.get("confidence", 0),
            "preview": c["text"][:100] + "...",
        }
        for c in all_chunks
    ]

    # Confidence = MAX of top-2 chunks
    sorted_conf = sorted([c.get("confidence", 0) for c in all_chunks], reverse=True)
    avg_confidence = max(sorted_conf[:2]) if sorted_conf else 0

    return {
        **state,
        "sub_questions": sub_questions,
        "findings": findings,
        "conflicts": conflicts,
        "verdict": verdict,
        "conditions": conditions,
        "retrieved_chunks": all_chunks,
        "final_answer": final_answer,
        "sources": sources,
        "confidence": avg_confidence,
        "agent_trace": trace,
    }
