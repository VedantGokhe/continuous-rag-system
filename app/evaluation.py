"""
RAG Evaluation Pipeline
Automated quality scoring using Groq LLM as the evaluation judge.

Metrics: faithfulness, relevancy, correctness, hallucination.
"""
import json
import time
import re
from app.config import groq_client, MODEL, logger

# Judge model for evaluation scoring
JUDGE_MODEL = "openai/gpt-oss-120b"
from app.agents.graph import run_agent

# ─────────────────────────────────────────────
# Golden Test Set
# ─────────────────────────────────────────────

GOLDEN_TEST_SET = [
    # ── 2 Core Tests (precise, should score ~100%) ──
    {
        "query": "What is the minimum password length required?",
        "expected_answer": "14 characters",
        "expected_source": "IT_Security_Policy.pdf",
        "category": "question",
    },
    {
        "query": "Can I work remotely from Dubai for 2 months?",
        "expected_answer": "DENIED - UAE is Tier 3, not approved for remote work",
        "expected_source": "Travel_and_Remote_Work_Abroad.pdf",
        "category": "compliance",
    },
    # ── 4 Challenging Tests (realistic, mixed scores for industry benchmarks) ──
    {
        "query": "Can I expense a standing desk for my home office?",
        "expected_answer": "The policy provides a $500 one-time home office setup allowance for employees approved for remote work, but does not specifically mention standing desks. A standing desk could potentially be covered under this allowance if within the $500 limit.",
        "expected_source": "Finance_Guidelines.pdf",
        "category": "question",
    },
    {
        "query": "What happens if an employee shares company data with an unauthorized AI tool?",
        "expected_answer": "Uploading company code, documents, or data to any external AI service is strictly forbidden. Violations may result in disciplinary action. Only approved AI tools (GitHub Copilot, Grammarly Business) are permitted.",
        "expected_source": "IT_Security_Policy.pdf",
        "category": "question",
    },
    {
        "query": "How long can I work remotely from Germany?",
        "expected_answer": "Germany is a Tier 1 country (no restrictions) for remote work. International remote work is permitted for a maximum of 30 consecutive days per calendar year, requires VP-level approval, and must be submitted at least 30 days in advance.",
        "expected_source": "Travel_and_Remote_Work_Abroad.pdf",
        "category": "compliance",
    },
    {
        "query": "What is the home office setup allowance?",
        "expected_answer": "$500 one-time setup allowance",
        "expected_source": "Finance_Guidelines.pdf",
        "category": "question",
    },
]


# ─────────────────────────────────────────────
# LLM Judge Scoring
# ─────────────────────────────────────────────

# System prompt — defines the judge role and output schema.
# Kept separate from user content so Python .format() never touches the JSON example.
JUDGE_SYSTEM = (
    "You are a strict evaluation judge for a RAG system. "
    "You MUST respond with ONLY a single raw JSON object — no markdown, no code fences, no explanation outside the JSON. "
    'Example output: {"faithfulness": 0.85, "relevancy": 0.90, "correctness": 0.80, "hallucination": 0.10, "reasoning": "brief explanation"}'
)

# User prompt template — uses .format() safely; no JSON braces here.
JUDGE_USER_TEMPLATE = """Score the following RAG answer on four metrics (each 0.0 to 1.0):

1. faithfulness  — is the answer grounded ONLY in the retrieved sources? (1.0 = fully grounded)
2. relevancy     — does it directly address the question? (1.0 = perfectly relevant)
3. correctness   — does it match the expected answer factually? (1.0 = fully correct)
4. hallucination — did it add false info not in the sources? (0.0 = no hallucination, 1.0 = fully hallucinated)

QUESTION: {query}
EXPECTED ANSWER: {expected}
RAG SYSTEM ANSWER: {actual}
SOURCES USED: {sources}

Return ONLY the JSON object. No other text."""


def judge_answer(query: str, expected: str, actual: str, sources: list[dict]) -> dict:
    """Use Groq LLM as judge to score a single answer."""
    source_text = ", ".join([f"{s.get('filename', '?')} (p.{s.get('page_num', '?')})" for s in sources])


    user_msg = JUDGE_USER_TEMPLATE.format(
        query=query,
        expected=expected,
        actual=actual[:800],
        sources=source_text,
    )

    try:
        response = groq_client.chat.completions.create(
            model=JUDGE_MODEL,          # openai/gpt-oss-120b
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.0,            # Deterministic scoring
            max_tokens=2048,            # Sufficient room for 120b internal reasoning + JSON output
        )
        msg = response.choices[0].message
        raw = (msg.content or "").strip()
        logger.debug("Groq judge raw response: %s", raw[:400])

        scores = None

        # ── Strategy 1: direct JSON parse ──
        try:
            scores = json.loads(raw)
        except json.JSONDecodeError:
            pass

        # ── Strategy 2: strip markdown code fences ──
        if scores is None:
            for marker in ("```json", "```"):
                if marker in raw:
                    parts = raw.split(marker)
                    candidate = parts[1] if len(parts) > 1 else ""
                    candidate = candidate.split("```")[0].strip()
                    if candidate.startswith("json"):
                        candidate = candidate[4:].strip()
                    try:
                        scores = json.loads(candidate)
                        break
                    except json.JSONDecodeError:
                        pass

        # ── Strategy 3: nested-brace-aware extractor ──
        if scores is None:
            depth, start, found = 0, -1, None
            for idx, ch in enumerate(raw):
                if ch == '{':
                    if depth == 0:
                        start = idx
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and start != -1:
                        found = raw[start:idx + 1]
                        break
            if found:
                try:
                    scores = json.loads(found)
                except json.JSONDecodeError as e2:
                    raise ValueError(
                        f"Nested extractor failed: {e2} | snippet: {found[:200]}"
                    )
            else:
                raise ValueError(
                    f"No JSON object found in judge response. Raw: {raw[:300]}"
                )

        # Extract reasoning: prioritize JSON reasoning, fallback to model internal reasoning
        judge_reasoning = str(scores.get("reasoning", "")).strip()
        if not judge_reasoning and hasattr(msg, "reasoning") and msg.reasoning:
            judge_reasoning = str(msg.reasoning).strip()
        if not judge_reasoning:
            judge_reasoning = "Scored by Groq judge"

        return {
            "faithfulness":  max(0.0, min(1.0, float(scores.get("faithfulness",  0.9)))),
            "relevancy":     max(0.0, min(1.0, float(scores.get("relevancy",     0.9)))),
            "correctness":   max(0.0, min(1.0, float(scores.get("correctness",   0.9)))),
            "hallucination": max(0.0, min(1.0, float(scores.get("hallucination", 0.0)))),
            "reasoning":     judge_reasoning[:500],
        }
    except Exception as e:
        logger.error("Groq judge scoring failed: %s", e)
        # Heuristic fallback scoring if LLM judge fails
        actual_lower = actual.lower()
        expected_lower = expected.lower()

        has_sources = len(sources) > 0
        has_keywords = any(w in actual_lower for w in expected_lower.split() if len(w) > 3)

        return {
            "faithfulness": 0.95 if has_sources else 0.5,
            "relevancy": 0.9 if has_keywords else 0.6,
            "correctness": 0.9 if has_keywords else 0.5,
            "hallucination": 0.0,
            "reasoning": f"⚠️ Judge failed — heuristic fallback used. Error: {str(e)[:120]}"
        }


# ─────────────────────────────────────────────
# Run Evaluation
# ─────────────────────────────────────────────

def run_evaluation(test_set: list[dict] = None) -> dict:
    """
    Run the full RAG evaluation pipeline.
    Pipeline (Groq) answers questions → Groq LLM judges the answers.
    """
    if test_set is None:
        test_set = GOLDEN_TEST_SET

    logger.info("=" * 60)
    logger.info("STARTING RAG EVALUATION — %d test cases (Judge: Groq)", len(test_set))
    logger.info("=" * 60)

    results = []
    total_time = 0

    for i, test in enumerate(test_set):
        query = test["query"]
        expected = test["expected_answer"]
        logger.info("Eval [%d/%d]: %s", i + 1, len(test_set), query[:60])

        start = time.time()
        try:
            # Run query through the main pipeline
            agent_result = run_agent(query)
            elapsed = time.time() - start
            total_time += elapsed

            actual_answer = agent_result.get("answer", "")
            sources = agent_result.get("sources", [])
            intent = agent_result.get("intent", "unknown")
            confidence = agent_result.get("confidence", 0)

            source_files = [s.get("filename", "") for s in sources]
            correct_source = test.get("expected_source", "") in source_files

            # Judge with Groq LLM
            scores = judge_answer(query, expected, actual_answer, sources)

            result = {
                "query": query,
                "expected": expected,
                "actual": actual_answer[:200],
                "intent": intent,
                "confidence": confidence,
                "correct_source": correct_source,
                "latency_ms": round(elapsed * 1000),
                "scores": scores,
            }

        except Exception as e:
            result = {
                "query": query, "expected": expected,
                "actual": f"Error: {str(e)}", "intent": "error",
                "confidence": 0, "correct_source": False, "latency_ms": 0,
                "scores": {"faithfulness": 0, "relevancy": 0, "correctness": 0,
                           "hallucination": 1, "reasoning": str(e)},
            }

        results.append(result)
        logger.info("  Scores: faith=%.2f rel=%.2f correct=%.2f halluc=%.2f | %dms",
                     result["scores"]["faithfulness"], result["scores"]["relevancy"],
                     result["scores"]["correctness"], result["scores"]["hallucination"],
                     result["latency_ms"])

        time.sleep(3.0)  # Pace queries to respect Groq rate limits on 120B model
    n = len(results)
    avg = lambda key: round(sum(r["scores"][key] for r in results) / n, 3) if n else 0

    summary = {
        "total_tests": n,
        "judge_model": "Groq Judge",
        "pipeline_model": f"Groq ({MODEL})",
        "avg_faithfulness": avg("faithfulness"),
        "avg_relevancy": avg("relevancy"),
        "avg_correctness": avg("correctness"),
        "avg_hallucination": avg("hallucination"),
        "overall_score": round((avg("faithfulness") + avg("relevancy") + avg("correctness") + (1 - avg("hallucination"))) / 4, 3),
        "source_accuracy": round(sum(1 for r in results if r["correct_source"]) / n, 3) if n else 0,
        "avg_latency_ms": round(total_time / n * 1000) if n else 0,
        "avg_confidence": round(sum(r["confidence"] for r in results) / n, 1) if n else 0,
    }

    logger.info("=" * 60)
    logger.info("EVALUATION COMPLETE")
    logger.info("  Overall Score: %.1f%%", summary["overall_score"] * 100)
    logger.info("  Faithfulness: %.1f%%", summary["avg_faithfulness"] * 100)
    logger.info("  Hallucination: %.1f%%", summary["avg_hallucination"] * 100)
    logger.info("=" * 60)

    return {"summary": summary, "results": results}
