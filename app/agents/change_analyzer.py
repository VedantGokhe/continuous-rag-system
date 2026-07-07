"""
Change Impact Analyzer Agent
Analyzes what changed when a document is updated and determines impact.

Flow:
1. Check for recent change reports in the database
2. If available, present the structured change analysis
3. If not, retrieve document info and summarize what the documents cover
"""
import json
from app.config import groq_client, MODEL, logger
from app.retrieval import retrieve
from app import database as db
from app.agents.state import AgentState


CHANGE_ANALYSIS_PROMPT = """You are a policy change analyst. Compare these two versions of a document and identify all meaningful changes.

Document: {filename}
Previous Version (v{old_version}):
{old_text_excerpt}

Current Version (v{new_version}):
{new_text_excerpt}

Analyze and respond ONLY with valid JSON:
{{
  "changes": [
    {{
      "section": "section or topic where change occurred",
      "old_value": "what it was before (brief)",
      "new_value": "what it is now (brief)",
      "severity": "HIGH" or "MEDIUM" or "LOW",
      "affected_parties": "who is affected by this change"
    }}
  ],
  "overall_severity": "HIGH" or "MEDIUM" or "LOW",
  "summary": "Brief 2-3 sentence summary of all changes"
}}"""


GENERAL_CHANGE_PROMPT = """You are a document change analyst. The user is asking about changes or updates to company policies.

Based on the following recent change reports and document information, provide a helpful summary.

Recent Change Reports:
{reports}

Currently Indexed Documents:
{documents}

User Question: {query}

Provide a clear, structured answer about what has changed. If no specific change data is available, explain what documents are currently indexed and suggest the user re-upload updated documents to trigger change detection."""


def analyze_document_changes(filename: str, old_text: str, new_text: str,
                             old_version: int, new_version: int) -> dict:
    """
    Analyze changes between two versions of a document using LLM.
    Called by the ingestion pipeline when a document is updated.
    Returns the change report.
    """
    # Truncate texts to fit in context window (keep first and last parts)
    max_chars = 4000
    old_excerpt = old_text[:max_chars] if len(old_text) <= max_chars else (
        old_text[:max_chars//2] + "\n...[truncated]...\n" + old_text[-max_chars//2:]
    )
    new_excerpt = new_text[:max_chars] if len(new_text) <= max_chars else (
        new_text[:max_chars//2] + "\n...[truncated]...\n" + new_text[-max_chars//2:]
    )

    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": CHANGE_ANALYSIS_PROMPT.format(
                    filename=filename,
                    old_version=old_version,
                    new_version=new_version,
                    old_text_excerpt=old_excerpt,
                    new_text_excerpt=new_excerpt,
                )
            }],
            temperature=0.1,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()

        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        report = json.loads(raw)

        # Store in database
        db.insert_change_report(
            filename=filename,
            old_version=old_version,
            new_version=new_version,
            changes=report.get("changes", []),
            severity=report.get("overall_severity", "LOW"),
        )

        logger.info("Change report generated for %s (v%d → v%d): %s severity",
                     filename, old_version, new_version, report.get("overall_severity"))
        return report

    except Exception as e:
        logger.error("Change analysis failed for %s: %s", filename, e)
        return {"changes": [], "overall_severity": "UNKNOWN",
                "summary": f"Change analysis error: {str(e)}"}


def change_analyzer_node(state: AgentState) -> AgentState:
    """
    Handle "what changed" queries.
    
    1. Check for existing change reports in the database
    2. Retrieve current document info
    3. Generate a comprehensive response about changes
    """
    query = state["query"]
    trace = state.get("agent_trace", [])
    trace.append("CHANGE_ANALYZER: Checking for document changes...")

    # Get recent change reports
    reports = db.get_change_reports(limit=5)
    trace.append(f"CHANGE_ANALYZER: Found {len(reports)} recent change reports")

    # Get indexed documents info
    all_docs = db.get_all_documents()
    doc_info = []
    for doc in all_docs:
        doc_info.append({
            "filename": doc[1],
            "base_name": doc[2],
            "version": doc[3],
            "chunks": doc[5],
            "indexed_at": doc[6],
        })

    # If we have change reports, format them
    if reports:
        report_text = ""
        for r in reports:
            report_text += f"\n📋 {r['filename']} (v{r['old_version']} → v{r['new_version']}) — {r['severity']} severity\n"
            for change in r.get("changes", []):
                report_text += f"  • [{change.get('severity', '?')}] {change.get('section', '?')}: "
                report_text += f"{change.get('old_value', '?')} → {change.get('new_value', '?')}\n"
                report_text += f"    Affected: {change.get('affected_parties', 'Unknown')}\n"

        trace.append("CHANGE_ANALYZER: Formatting change reports")

        # Also retrieve relevant chunks for additional context
        chunks = retrieve(query, top_k=3)

        try:
            response = groq_client.chat.completions.create(
                model=MODEL,
                messages=[{
                    "role": "user",
                    "content": GENERAL_CHANGE_PROMPT.format(
                        reports=report_text,
                        documents=json.dumps(doc_info, indent=2),
                        query=query,
                    )
                }],
                temperature=0.2,
                max_tokens=800,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            answer = f"Change reports found but summary generation failed: {str(e)}\n\nRaw reports:\n{report_text}"

        change_report = {
            "reports": reports,
            "documents": doc_info,
        }
    else:
        # No change reports — give a short, clear response (Fix #9: less verbose)
        trace.append("CHANGE_ANALYZER: No change reports found")
        chunks = []

        doc_names = [d["filename"] for d in doc_info]
        answer = (
            f"No changes detected yet. The following {len(doc_info)} document(s) are currently indexed "
            f"as their initial versions:\n\n"
            + "\n".join([f"• {d['filename']} (v{d['version']})" for d in doc_info])
            + "\n\nTo trigger change tracking, upload an updated version of any document. "
            "The system will automatically detect what changed, assess the impact, and generate a detailed change report."
        )

        change_report = {
            "reports": [],
            "documents": doc_info,
            "note": "Upload updated documents to trigger change detection."
        }

    sources = [
        {
            "filename": c["filename"],
            "page_num": c["page_num"],
            "version": c["version"],
            "confidence": c.get("confidence", 0),
            "preview": c["text"][:100] + "...",
        }
        for c in chunks
    ] if 'chunks' in dir() and chunks else []

    avg_confidence = sum(c.get("confidence", 0) for c in chunks) / len(chunks) if chunks else 0

    return {
        **state,
        "change_report": change_report,
        "final_answer": answer,
        "sources": sources,
        "confidence": avg_confidence,
        "agent_trace": trace,
    }
