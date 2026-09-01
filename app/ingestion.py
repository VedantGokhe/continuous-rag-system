"""
Continuous-RAG Document Ingestion (v2 — Fixed)

Fixes applied:
  Issue #1:  Sentence-aware chunking (never cuts mid-sentence)
  Issue #4:  Cosine similarity via IndexFlatIP (accurate confidence scores)
  Issue #6:  Better chunks = better retrieval of specific facts
  Issue #10: Text cleaning removes PDF artifacts before embedding
"""
import os
import re
import hashlib
import numpy as np
from pypdf import PdfReader

from app import vector_store
from app.config import (
    embedding_model, DOCUMENTS_DIR, INDEX_DIR, INDEX_PATH,
    CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_DIMENSION, logger
)
from app import database as db


# ─────────────────────────────────────────────
# Text Cleaning (Fix #10)
# ─────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Remove PDF artifacts, decorative chars, normalize whitespace."""
    # Remove decorative unicode (lines, blocks, shapes)
    text = re.sub(r'[━─═▬▄▀░▒▓█■□▪▫●○◆◇★☆►◄▲▼•·]+', ' ', text)
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove very short lines (likely headers/footers/page numbers)
    lines = text.split('\n')
    cleaned = [l.strip() for l in lines if len(l.strip()) > 5]
    return '\n'.join(cleaned).strip()


# ─────────────────────────────────────────────
# Sentence-Aware Chunking (Fix #1, #6)
# ─────────────────────────────────────────────

def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences/clauses."""
    # Split on sentence endings followed by space+capital, or double newlines
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])|(?<=[.!?])\n|\n{2,}', text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 10]


def create_chunks(page_texts: list[str]) -> list[dict]:
    """
    Sentence-aware chunking — groups complete sentences into chunks.
    Never cuts mid-sentence. Maintains overlap for context continuity.
    """
    chunks = []
    chunk_idx = 0

    for page_num, page_text in enumerate(page_texts):
        cleaned = clean_text(page_text)
        if not cleaned:
            continue

        sentences = split_into_sentences(cleaned)
        if not sentences:
            continue

        current_sentences = []
        current_length = 0

        for sentence in sentences:
            if current_length + len(sentence) > CHUNK_SIZE and current_sentences:
                # Save current chunk
                chunk_text = " ".join(current_sentences)
                if len(chunk_text) > 30:
                    chunks.append({
                        "text": chunk_text,
                        "index": chunk_idx,
                        "page_num": page_num + 1,
                    })
                    chunk_idx += 1
                # Keep last N sentences for overlap
                current_sentences = current_sentences[-CHUNK_OVERLAP:]
                current_length = sum(len(s) for s in current_sentences)

            current_sentences.append(sentence)
            current_length += len(sentence)

        # Last chunk on this page
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            if len(chunk_text) > 30:
                chunks.append({
                    "text": chunk_text,
                    "index": chunk_idx,
                    "page_num": page_num + 1,
                })
                chunk_idx += 1

    return chunks


# ─────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────

def get_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file for change detection."""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def extract_base_name_and_version(filename: str) -> tuple[str, int]:
    """Extract base filename and version number."""
    clean_name = filename
    if filename.endswith('.pdf.pdf'):
        clean_name = filename[:-4]
    match = re.match(r'^(.+?)_v(\d+)(\.pdf)$', clean_name)
    if match:
        return match.group(1) + match.group(3), int(match.group(2))
    return clean_name, 1


def extract_text_from_pdf(filepath: str) -> tuple[str, int, list[str]]:
    """Extract text from PDF. Returns (full_text, page_count, page_texts)."""
    reader = PdfReader(filepath)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page_texts), len(reader.pages), page_texts


# ─────────────────────────────────────────────
# FAISS Index — Cosine Similarity (Fix #4)
# ─────────────────────────────────────────────

def load_or_create_index():
    """Load or create vector index using Inner Product (= cosine for normalized vectors)."""
    os.makedirs(INDEX_DIR, exist_ok=True)
    if os.path.exists(INDEX_PATH) or os.path.exists(INDEX_PATH + ".npz"):
        try:
            index = vector_store.read_index(INDEX_PATH)
            logger.info("Loaded vector index with %d vectors", index.ntotal)
            return index
        except Exception as e:
            logger.warning("Failed to load index, creating new: %s", e)

    # IndexFlatIP = Inner Product = cosine similarity for normalized vectors
    base_index = vector_store.IndexFlatIP(EMBEDDING_DIMENSION)
    index = vector_store.IndexIDMap(base_index)
    logger.info("Created new Vector IndexIDMap (cosine similarity)")
    return index


def save_index(index):
    """Save vector index to disk."""
    os.makedirs(INDEX_DIR, exist_ok=True)
    vector_store.write_index(index, INDEX_PATH)
    logger.info("Saved vector index (%d vectors)", index.ntotal)


def add_to_index(index, chunk_texts: list[str], chunk_ids: list[int]):
    """Encode, normalize, and add to vector store."""
    if not chunk_texts:
        return
    embeddings = embedding_model.encode(chunk_texts)
    embeddings = np.array(embeddings, dtype=np.float32)
    vector_store.normalize_L2(embeddings)  # Normalize for cosine similarity
    ids = np.array(chunk_ids, dtype=np.int64)
    index.add_with_ids(embeddings, ids)
    logger.info("Added %d normalized vectors to index", len(chunk_ids))


def remove_from_index(index, chunk_ids: list[int]):
    """Remove vectors from index by IDs."""
    if not chunk_ids:
        return
    ids = np.array(chunk_ids, dtype=np.int64)
    index.remove_ids(ids)
    logger.info("Removed %d vectors from index", len(chunk_ids))


# ─────────────────────────────────────────────
# Core Ingestion Logic
# ─────────────────────────────────────────────

def get_latest_version_files(files: list[str]) -> dict:
    """Return only the latest version of each base document."""
    file_versions = {}
    for f in files:
        if not f.endswith('.pdf'):
            continue
        base_name, version = extract_base_name_and_version(f)
        if base_name not in file_versions or version > file_versions[base_name][1]:
            file_versions[base_name] = (f, version)
    return file_versions


def ingest_single_document(filename: str, index) -> dict:
    """Ingest a single document with hash-based change detection."""
    filepath = os.path.join(DOCUMENTS_DIR, filename)
    if not os.path.exists(filepath):
        return {"filename": filename, "action": "skipped", "reason": "file not found"}

    new_hash = get_file_hash(filepath)
    stored_hash = db.get_document_hash(filename)
    stored_chunk_ids = db.get_chunk_ids_for_document(filename)
    index_has_vectors = (index.ntotal > 0) and (len(stored_chunk_ids) > 0)

    if stored_hash and stored_hash == new_hash and index_has_vectors:
        logger.info("SKIP (unchanged): %s", filename)
        return {"filename": filename, "action": "skipped", "reason": "unchanged (hash match)"}

    base_name, version = extract_base_name_and_version(filename)
    old_text = db.get_document_text(filename)

    if stored_hash:
        logger.info("UPDATE (hash changed): %s", filename)
        old_chunk_ids = db.get_chunk_ids_for_document(filename)
        remove_from_index(index, old_chunk_ids)
        db.delete_document(filename)
        action = "updated"
    else:
        logger.info("NEW: %s", filename)
        action = "added"

    try:
        full_text, page_count, page_texts = extract_text_from_pdf(filepath)
    except Exception as e:
        logger.error("Failed to read PDF %s: %s", filename, e)
        return {"filename": filename, "action": "error", "reason": str(e)}

    if not full_text.strip():
        return {"filename": filename, "action": "skipped", "reason": "no text extracted"}

    chunks = create_chunks(page_texts)
    if not chunks:
        return {"filename": filename, "action": "skipped", "reason": "no chunks created"}

    doc_id = db.insert_document(
        filename=filename, base_name=base_name, file_hash=new_hash,
        version=version, full_text=full_text, page_count=page_count,
        chunk_count=len(chunks)
    )
    chunk_ids = db.insert_chunks(doc_id, chunks)
    add_to_index(index, [c["text"] for c in chunks], chunk_ids)

    logger.info("  ✓ %s: %d chunks, %d pages (v%d)", filename, len(chunks), page_count, version)
    return {
        "filename": filename, "action": action, "version": version,
        "chunks": len(chunks), "pages": page_count,
        "old_text": old_text, "new_text": full_text,
    }


def process_documents() -> dict:
    """Main ingestion pipeline with hash-based incremental indexing."""
    logger.info("=" * 60)
    logger.info("STARTING INCREMENTAL DOCUMENT SYNC")
    logger.info("=" * 60)

    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    all_files = [f for f in os.listdir(DOCUMENTS_DIR) if f.endswith('.pdf')]
    if not all_files:
        return {"status": "warning", "message": "No PDF files found", "files": []}

    latest_files = get_latest_version_files(all_files)
    index = load_or_create_index()

    results = []
    for base_name, (filename, version) in latest_files.items():
        results.append(ingest_single_document(filename, index))

    # Remove deleted files
    db_docs = db.get_all_documents()
    disk_files = {info[0] for info in latest_files.values()}
    for doc in db_docs:
        if doc[1] not in disk_files:
            old_ids = db.get_chunk_ids_for_document(doc[1])
            remove_from_index(index, old_ids)
            db.delete_document(doc[1])
            results.append({"filename": doc[1], "action": "removed"})

    save_index(index)

    added = sum(1 for r in results if r.get("action") == "added")
    updated = sum(1 for r in results if r.get("action") == "updated")
    skipped = sum(1 for r in results if r.get("action") == "skipped")
    removed = sum(1 for r in results if r.get("action") == "removed")

    logger.info("SYNC: +%d added, ~%d updated, =%d skipped, -%d removed | Total: %d vectors",
                added, updated, skipped, removed, index.ntotal)

    return {
        "status": "success", "total_vectors": index.ntotal,
        "files_processed": len(results), "added": added, "updated": updated,
        "skipped": skipped, "removed": removed, "details": results,
        "latest_versions": [{"filename": f, "version": v} for _, (f, v) in latest_files.items()]
    }
