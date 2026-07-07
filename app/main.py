"""
Continuous-RAG: Enterprise Policy Intelligence System
FastAPI application with multi-agent AI, continuous ingestion, and real-time file watching.
"""
import os
from contextlib import asynccontextmanager

import json as json_lib

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.config import logger, DOCUMENTS_DIR, groq_client, MODEL
from app.ingestion import process_documents
from app.retrieval import retrieve
from app.watcher import start_watcher, stop_watcher, is_watching
from app.agents.graph import run_agent
from app.agents.change_analyzer import analyze_document_changes
from app.ingestion import extract_base_name_and_version
from app import database as db


# ─────────────────────────────────────────────
# Lifespan — Start/Stop file watcher
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: start file watcher. Shutdown: stop it."""
    logger.info("🚀 Starting Continuous-RAG server...")
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    start_watcher()
    yield
    logger.info("Shutting down...")
    stop_watcher()


# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────

app = FastAPI(
    title="Continuous-RAG",
    description="Enterprise Policy Intelligence System with AI Agents",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Health & Status Endpoints
# ─────────────────────────────────────────────

@app.get("/")
def root():
    """Health check and API overview."""
    return {
        "status": "online",
        "title": "Continuous-RAG — Enterprise Policy Intelligence",
        "version": "2.0.0",
        "features": [
            "Multi-agent AI (Router → Retriever / Compliance / Change Analyzer)",
            "Hash-based incremental indexing (no full rebuilds)",
            "File watcher for continuous document sync",
            "Page-level source citations",
            "Query history & change reports",
        ],
        "endpoints": {
            "POST /upload": "Upload a PDF document",
            "GET /sync": "Trigger incremental document sync",
            "GET /query?q=question": "Ask via agent pipeline (auto-routes intent)",
            "GET /status": "System status and indexed documents",
            "GET /history": "Query history",
            "GET /changes": "Document change reports",
        },
        "watcher": "active" if is_watching() else "inactive",
    }


@app.get("/status")
def status():
    """Detailed system status — indexed documents, watcher state, index stats."""
    docs = db.get_all_documents()
    
    indexed_files = []
    for doc in docs:
        indexed_files.append({
            "filename": doc[1],
            "base_name": doc[2],
            "version": doc[3],
            "file_hash": doc[4][:12] + "...",  # Truncated for display
            "chunks": doc[5],
            "indexed_at": doc[6],
        })

    return {
        "status": "online",
        "watcher": "active" if is_watching() else "inactive",
        "total_documents": len(docs),
        "indexed_files": indexed_files,
    }


# ─────────────────────────────────────────────
# Document Management
# ─────────────────────────────────────────────

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document.
    The file watcher will auto-detect it, OR call /sync manually.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")

    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    filepath = os.path.join(DOCUMENTS_DIR, file.filename)

    try:
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)

        logger.info("Uploaded: %s (%d bytes)", file.filename, len(content))

        return {
            "status": "uploaded",
            "filename": file.filename,
            "size_bytes": len(content),
            "message": "File watcher will auto-index in ~3 seconds, or call GET /sync",
        }
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")


@app.get("/sync")
def sync_documents():
    """
    Trigger incremental document sync.
    Uses hash-based change detection — only processes new/modified files.
    """
    try:
        result = process_documents()

        # Check if any documents were updated (not just added) and trigger change analysis
        for detail in result.get("details", []):
            if detail.get("action") == "updated" and detail.get("old_text") and detail.get("new_text"):
                logger.info("Triggering change analysis for: %s", detail["filename"])
                _, old_version = extract_base_name_and_version(detail["filename"])
                analyze_document_changes(
                    filename=detail["filename"],
                    old_text=detail["old_text"],
                    new_text=detail["new_text"],
                    old_version=max(1, detail.get("version", 1) - 1),
                    new_version=detail.get("version", 1),
                )

        # Clean up internal fields from response
        clean_details = []
        for d in result.get("details", []):
            clean_details.append({
                "filename": d.get("filename"),
                "action": d.get("action"),
                "version": d.get("version"),
                "chunks": d.get("chunks"),
                "reason": d.get("reason"),
            })
        result["details"] = clean_details

        return result
    except Exception as e:
        logger.error("Sync failed: %s", e)
        raise HTTPException(500, f"Sync failed: {str(e)}")


# ─────────────────────────────────────────────
# Query — Agent Pipeline (Fix #2: conversation memory)
# ─────────────────────────────────────────────

class QueryRequest(BaseModel):
    q: str
    chat_history: list[dict] = []  # [{role: "user"|"assistant", content: "..."}]


@app.post("/query")
def query_post(req: QueryRequest):
    """
    Query via POST with conversation history for follow-up support.
    The Router agent rewrites vague queries using chat_history.
    """
    if not req.q or not req.q.strip():
        raise HTTPException(400, "Query field 'q' is required")
    try:
        result = run_agent(req.q.strip(), chat_history=req.chat_history)
        return result
    except Exception as e:
        logger.error("Query failed: %s", e)
        raise HTTPException(500, f"Query failed: {str(e)}")


@app.get("/query")
def query_get(q: str):
    """Query via GET (no history, for simple/curl testing)."""
    if not q or not q.strip():
        raise HTTPException(400, "Query parameter 'q' is required")
    try:
        return run_agent(q.strip())
    except Exception as e:
        logger.error("Query failed: %s", e)
        raise HTTPException(500, f"Query failed: {str(e)}")


# ─────────────────────────────────────────────
# Document Management — Clear & Delete
# ─────────────────────────────────────────────

@app.post("/clear")
def clear_all():
    """Clear ALL data — wipe database, delete FAISS index, delete all PDFs."""
    import shutil
    from app.config import INDEX_DIR
    try:
        db.wipe_all()
        if os.path.exists(INDEX_DIR):
            shutil.rmtree(INDEX_DIR)
            os.makedirs(INDEX_DIR, exist_ok=True)
        # Delete all PDFs from documents folder
        if os.path.exists(DOCUMENTS_DIR):
            for f in os.listdir(DOCUMENTS_DIR):
                if f.endswith('.pdf'):
                    os.remove(os.path.join(DOCUMENTS_DIR, f))
        logger.info("CLEAR ALL: Database wiped, index deleted, PDFs removed")
        return {"status": "cleared", "message": "All data cleared successfully"}
    except Exception as e:
        raise HTTPException(500, f"Clear failed: {str(e)}")


@app.delete("/document/{filename}")
def delete_document(filename: str):
    """Delete a specific document — removes from DB, FAISS index, and disk."""
    from app.ingestion import load_or_create_index, remove_from_index, save_index
    try:
        # Remove from FAISS
        chunk_ids = db.get_chunk_ids_for_document(filename)
        if chunk_ids:
            index = load_or_create_index()
            remove_from_index(index, chunk_ids)
            save_index(index)
        # Remove from DB
        db.delete_document(filename)
        # Remove file from disk
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        logger.info("Deleted document: %s", filename)
        return {"status": "deleted", "filename": filename}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")


# ─────────────────────────────────────────────
# Document Viewer (Fix #11)
# ─────────────────────────────────────────────

@app.get("/document/{filename}")
def get_document_text(filename: str):
    """Get the full text of an indexed document for viewing (cleaned)."""
    from app.ingestion import clean_text
    text = db.get_document_text(filename)
    if text is None:
        raise HTTPException(404, f"Document '{filename}' not found")
    return {"filename": filename, "text": clean_text(text)}


# ─────────────────────────────────────────────
# Streaming Query (SSE) — word-by-word response
# ─────────────────────────────────────────────

@app.post("/query/stream")
def query_stream(req: QueryRequest):
    """
    Streaming query — retrieves chunks, then streams LLM answer via SSE.
    First sends metadata (intent, sources), then streams answer tokens.
    """
    if not req.q or not req.q.strip():
        raise HTTPException(400, "Query field 'q' is required")

    query = req.q.strip()

    def generate():
        try:
            # Step 1: Retrieve chunks
            chunks = retrieve(query, top_k=5)
            sources = [{"filename": c["filename"], "page_num": c["page_num"],
                        "version": c["version"], "confidence": c.get("confidence", 0),
                        "preview": c["text"][:100] + "..."} for c in chunks]

            sorted_conf = sorted([c.get("confidence", 0) for c in chunks], reverse=True)
            confidence = max(sorted_conf[:2]) if sorted_conf else 0

            # Send metadata first
            yield f"data: {json_lib.dumps({'type': 'meta', 'intent': 'question', 'sources': sources, 'confidence': confidence})}\n\n"

            if not chunks:
                yield f"data: {json_lib.dumps({'type': 'token', 'content': 'No relevant documents found.'})}\n\n"
                yield f"data: {json_lib.dumps({'type': 'done'})}\n\n"
                return

            # Build context
            context = "\n\n---\n\n".join([
                f"[Source: {c['filename']}, Page {c['page_num']}]\n{c['text']}" for c in chunks
            ])

            prompt = f"""You are a helpful enterprise assistant. Answer based ONLY on the context below.
Be concise. Cite the source document and page.
If the context doesn't answer the question, say "I don't have enough information."

Context:
{context}

Question: {query}

Answer:"""

            # Step 2: Stream LLM response
            stream = groq_client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield f"data: {json_lib.dumps({'type': 'token', 'content': token})}\n\n"

            yield f"data: {json_lib.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json_lib.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─────────────────────────────────────────────
# RAG Evaluation Pipeline
# ─────────────────────────────────────────────

@app.get("/eval")
def run_eval():
    """Run the RAG evaluation pipeline against golden test set. Takes ~30-60 seconds."""
    from app.evaluation import run_evaluation
    try:
        result = run_evaluation()
        return result
    except Exception as e:
        logger.error("Evaluation failed: %s", e)
        raise HTTPException(500, f"Evaluation failed: {str(e)}")


# ─────────────────────────────────────────────
# History & Reports
# ─────────────────────────────────────────────

@app.get("/history")
def query_history(limit: int = 50):
    """Get recent query history with answers and metadata."""
    try:
        history = db.get_query_history(limit=limit)
        return {
            "total": len(history),
            "queries": history,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch history: {str(e)}")


@app.get("/changes")
def change_reports(filename: str = None, limit: int = 10):
    """Get document change reports. Optionally filter by filename."""
    try:
        reports = db.get_change_reports(filename=filename, limit=limit)
        return {
            "total": len(reports),
            "reports": reports,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch change reports: {str(e)}")
