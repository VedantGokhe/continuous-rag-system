"""
Continuous-RAG Database Layer
SQLite database with tables for documents, chunks, change reports, and query history.
Uses hash-based tracking for incremental indexing.
"""
import sqlite3
import json
from datetime import datetime
from app.config import DB_PATH, logger

# --- Connection ---
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
conn.execute("PRAGMA foreign_keys=ON")
cursor = conn.cursor()

# --- Schema ---
cursor.executescript("""
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE,
    base_name TEXT,
    file_hash TEXT,
    version INTEGER DEFAULT 1,
    full_text TEXT,
    page_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_num INTEGER DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS change_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    old_version INTEGER,
    new_version INTEGER,
    changes_json TEXT,
    severity TEXT DEFAULT 'LOW',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    answer TEXT,
    intent TEXT DEFAULT 'question',
    sources_json TEXT,
    confidence REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doc_filename ON documents(filename);
CREATE INDEX IF NOT EXISTS idx_doc_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_change_filename ON change_reports(filename);
""")
conn.commit()
logger.info("Database initialized at %s", DB_PATH)


# --- Document Operations ---

def get_document_by_filename(filename: str):
    """Get a document record by filename."""
    cursor.execute("SELECT * FROM documents WHERE filename = ?", (filename,))
    return cursor.fetchone()


def get_document_hash(filename: str) -> str | None:
    """Get stored hash for a filename. Returns None if not found."""
    cursor.execute("SELECT file_hash FROM documents WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_all_documents():
    """Get all indexed documents."""
    cursor.execute("SELECT id, filename, base_name, version, file_hash, chunk_count, indexed_at FROM documents ORDER BY filename")
    return cursor.fetchall()


def get_document_text(filename: str) -> str | None:
    """Get full text of a document (used for change analysis)."""
    cursor.execute("SELECT full_text FROM documents WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    return row[0] if row else None


def insert_document(filename: str, base_name: str, file_hash: str, version: int,
                    full_text: str, page_count: int, chunk_count: int) -> int:
    """Insert a new document record. Returns the document ID."""
    cursor.execute("""
        INSERT OR REPLACE INTO documents 
        (filename, base_name, file_hash, version, full_text, page_count, chunk_count, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (filename, base_name, file_hash, version, full_text, page_count, chunk_count,
          datetime.now().isoformat()))
    conn.commit()
    return cursor.lastrowid


def delete_document(filename: str):
    """Delete a document and its chunks (CASCADE)."""
    cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
    conn.commit()


# --- Chunk Operations ---

def insert_chunks(document_id: int, chunks: list[dict]) -> list[int]:
    """
    Insert chunks for a document. Returns list of chunk IDs (used as FAISS IDs).
    Each chunk dict has: {text, index, page_num}
    """
    chunk_ids = []
    for chunk in chunks:
        cursor.execute("""
            INSERT INTO chunks (document_id, chunk_text, chunk_index, page_num)
            VALUES (?, ?, ?, ?)
        """, (document_id, chunk["text"], chunk["index"], chunk.get("page_num", 0)))
        chunk_ids.append(cursor.lastrowid)
    conn.commit()
    return chunk_ids


def get_chunks_by_document(document_id: int) -> list[tuple]:
    """Get all chunks for a document."""
    cursor.execute("SELECT id, chunk_text, chunk_index, page_num FROM chunks WHERE document_id = ?",
                   (document_id,))
    return cursor.fetchall()


def get_chunk_ids_for_document(filename: str) -> list[int]:
    """Get all chunk IDs (FAISS IDs) for a document by filename."""
    cursor.execute("""
        SELECT c.id FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.filename = ?
    """, (filename,))
    return [row[0] for row in cursor.fetchall()]


def get_chunks_by_ids(chunk_ids: list[int]) -> list[dict]:
    """Get chunk details by their IDs. Used after FAISS search returns IDs."""
    if not chunk_ids:
        return []
    placeholders = ",".join("?" * len(chunk_ids))
    cursor.execute(f"""
        SELECT c.id, c.chunk_text, c.chunk_index, c.page_num,
               d.filename, d.base_name, d.version
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.id IN ({placeholders})
    """, chunk_ids)
    rows = cursor.fetchall()
    return [
        {
            "chunk_id": row[0],
            "text": row[1],
            "chunk_index": row[2],
            "page_num": row[3],
            "filename": row[4],
            "base_name": row[5],
            "version": row[6],
        }
        for row in rows
    ]


# --- Change Report Operations ---

def insert_change_report(filename: str, old_version: int, new_version: int,
                         changes: list[dict], severity: str) -> int:
    """Insert a change impact report."""
    cursor.execute("""
        INSERT INTO change_reports (filename, old_version, new_version, changes_json, severity)
        VALUES (?, ?, ?, ?, ?)
    """, (filename, old_version, new_version, json.dumps(changes), severity))
    conn.commit()
    return cursor.lastrowid


def get_change_reports(filename: str = None, limit: int = 10) -> list[dict]:
    """Get change reports, optionally filtered by filename."""
    if filename:
        cursor.execute("""
            SELECT id, filename, old_version, new_version, changes_json, severity, created_at
            FROM change_reports WHERE filename = ? ORDER BY created_at DESC LIMIT ?
        """, (filename, limit))
    else:
        cursor.execute("""
            SELECT id, filename, old_version, new_version, changes_json, severity, created_at
            FROM change_reports ORDER BY created_at DESC LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "filename": row[1],
            "old_version": row[2],
            "new_version": row[3],
            "changes": json.loads(row[4]) if row[4] else [],
            "severity": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


# --- Query History Operations ---

def insert_query_history(query: str, answer: str, intent: str,
                         sources: list[dict], confidence: float):
    """Save a query and its answer to history."""
    cursor.execute("""
        INSERT INTO query_history (query, answer, intent, sources_json, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (query, answer, intent, json.dumps(sources), confidence))
    conn.commit()


def get_query_history(limit: int = 50) -> list[dict]:
    """Get recent query history."""
    cursor.execute("""
        SELECT id, query, answer, intent, sources_json, confidence, created_at
        FROM query_history ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "query": row[1],
            "answer": row[2],
            "intent": row[3],
            "sources": json.loads(row[4]) if row[4] else [],
            "confidence": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


# --- Utility ---

def wipe_all():
    """Nuclear clean - delete all data from all tables."""
    cursor.executescript("""
        DELETE FROM chunks;
        DELETE FROM documents;
        DELETE FROM change_reports;
        DELETE FROM query_history;
    """)
    conn.commit()
    logger.info("Database wiped clean.")
