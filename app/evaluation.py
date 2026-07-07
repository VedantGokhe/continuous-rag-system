"""
RAG Evaluation Pipeline
Automated quality scoring using Gemini 2.5 Pro as the evaluation judge.

Main pipeline (Q&A) uses Groq (Llama) for speed.
Evaluation judge uses Gemini 2.5 Pro (Vertex AI) for accuracy.

Metrics: faithfulness, relevancy, correctness, hallucination.
"""
import json
import time
import os
from app.config import logger
from app.agents.graph import run_agent

# ─────────────────────────────────────────────
# Gemini Judge Client (Vertex AI)
# ─────────────────────────────────────────────

GCP_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gcp-key.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_KEY_PATH

_gemini_model = None

def get_gemini_model():
    """Lazy-load Gemini model to avoid startup delay."""
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        genai.configure()
        # Use Vertex AI service account credentials
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(
            GCP_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        import vertexai
        vertexai.init(project="ambitio-ds-v2", location="us-central1", credentials=credentials)
        from vertexai.generative_models import GenerativeModel
        _gemini_model = GenerativeModel("gemini-2.5-pro")
        logger.info("Gemini 2.5 Pro loaded as evaluation judge")
    return _gemini_model


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
# Gemini Judge Scoring
# ─────────────────────────────────────────────

JUDGE_PROMPT = """You are a strict evaluation judge for a RAG (Retrieval-Augmented Generation) system. Score the AI's answer accurately.

Question asked: {query}
Expected correct answer: {expected}
AI system's actual answer: {actual}
Documents retrieved as sources: {sources}

Score EACH metric from 0.0 to 1.0. Be precise and honest:

1. faithfulness (0.0-1.0): Does the AI's answer ONLY use information that could come from the retrieved documents? 1.0 = completely grounded in sources. 0.0 = entirely made up.

2. relevancy (0.0-1.0): Does the answer address the question that was asked? 1.0 = directly answers the question. 0.0 = completely off-topic.

3. correctness (0.0-1.0): Is the factual content of the answer correct when compared to the expected answer? 1.0 = matches expected answer. 0.0 = completely wrong.

4. hallucination (0.0-1.0): Did the AI add false information not supported by the sources? 0.0 = no hallucination (good). 1.0 = completely hallucinated (bad).

Respond with ONLY valid JSON, no markdown:
{{"faithfulness": 0.0, "relevancy": 0.0, "correctness": 0.0, "hallucination": 0.0, "reasoning": "explanation"}}"""


def judge_answer(query: str, expected: str, actual: str, sources: list[dict]) -> dict:
    """Use Gemini 2.5 Pro as judge to score a single answer."""
    source_text = ", ".join([f"{s.get('filename', '?')} (p.{s.get('page_num', '?')})" for s in sources])

    try:
        model = get_gemini_model()
        prompt = JUDGE_PROMPT.format(
            query=query, expected=expected,
            actual=actual[:500], sources=source_text
        )

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Clean JSON from markdown blocks if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        scores = json.loads(raw)
        return {
            "faithfulness": float(scores.get("faithfulness", 0)),
            "relevancy": float(scores.get("relevancy", 0)),
            "correctness": float(scores.get("correctness", 0)),
            "hallucination": float(scores.get("hallucination", 0)),
            "reasoning": scores.get("reasoning", ""),
        }
    except Exception as e:
        logger.error("Gemini judge scoring failed: %s", e)
        return {
            "faithfulness": 0, "relevancy": 0, "correctness": 0,
            "hallucination": 1, "reasoning": f"Judge error: {str(e)}"
        }


# ─────────────────────────────────────────────
# Run Evaluation
# ─────────────────────────────────────────────

def run_evaluation(test_set: list[dict] = None) -> dict:
    """
    Run the full RAG evaluation pipeline.
    Pipeline (Groq) answers questions → Gemini 2.5 Pro judges the answers.
    """
    if test_set is None:
        test_set = GOLDEN_TEST_SET

    logger.info("=" * 60)
    logger.info("STARTING RAG EVALUATION — %d test cases (Judge: Gemini 2.5 Pro)", len(test_set))
    logger.info("=" * 60)

    results = []
    total_time = 0

    for i, test in enumerate(test_set):
        query = test["query"]
        expected = test["expected_answer"]
        logger.info("Eval [%d/%d]: %s", i + 1, len(test_set), query[:60])

        start = time.time()
        try:
            # Run query through the main pipeline (Groq/Llama)
            agent_result = run_agent(query)
            elapsed = time.time() - start
            total_time += elapsed

            actual_answer = agent_result.get("answer", "")
            sources = agent_result.get("sources", [])
            intent = agent_result.get("intent", "unknown")
            confidence = agent_result.get("confidence", 0)

            source_files = [s.get("filename", "") for s in sources]
            correct_source = test.get("expected_source", "") in source_files

            # Judge with Gemini 2.5 Pro
            time.sleep(2)  # Rate limit buffer
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

        time.sleep(1)

    # Aggregate
    n = len(results)
    avg = lambda key: round(sum(r["scores"][key] for r in results) / n, 3) if n else 0

    summary = {
        "total_tests": n,
        "judge_model": "Gemini 2.5 Pro",
        "pipeline_model": "Groq (Llama 3.1)",
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
    logger.info("EVALUATION COMPLETE (Judge: Gemini 2.5 Pro)")
    logger.info("  Overall Score: %.1f%%", summary["overall_score"] * 100)
    logger.info("  Faithfulness: %.1f%%", summary["avg_faithfulness"] * 100)
    logger.info("  Hallucination: %.1f%%", summary["avg_hallucination"] * 100)
    logger.info("=" * 60)

    return {"summary": summary, "results": results}
