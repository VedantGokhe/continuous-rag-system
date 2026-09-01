"""
Continuous-RAG Retrieval Engine (v2 — Fixed)

Fixes applied:
  Issue #1:  Hybrid retrieval (semantic + keyword boosting)
  Issue #4:  Correct confidence from cosine similarity [0-100%]
  Issue #6:  Keyword boost ensures exact term matches (e.g. "ChatGPT") surface
"""
import os
import re
import numpy as np

from app import vector_store
from app.config import embedding_model, reranker_model, INDEX_PATH, EMBEDDING_DIMENSION, logger
from app import database as db


def load_index():
    """Load vector index from disk."""
    if not os.path.exists(INDEX_PATH) and not os.path.exists(INDEX_PATH + ".npz"):
        logger.warning("No vector index found at %s", INDEX_PATH)
        return None
    try:
        return vector_store.read_index(INDEX_PATH)
    except Exception as e:
        logger.error("Failed to load vector index: %s", e)
        return None


def keyword_score(query: str, chunk_text: str) -> float:
    """
    Simple keyword matching score (0.0 to 1.0).
    Boosts chunks that contain exact query terms.
    
    This is the "keyword" half of hybrid retrieval.
    Catches cases where semantic embeddings miss exact terms
    (e.g., "ChatGPT" as a proper noun).
    """
    # Extract meaningful words (3+ chars, not stopwords)
    stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has',
                 'her', 'was', 'one', 'our', 'out', 'what', 'with', 'how', 'who', 'get',
                 'from', 'this', 'that', 'they', 'have', 'been', 'make', 'like', 'will',
                 'when', 'your', 'said', 'each', 'which', 'their', 'about', 'would', 'there'}
    
    query_words = [w.lower() for w in re.findall(r'\b\w+\b', query) 
                   if len(w) >= 3 and w.lower() not in stopwords]
    
    if not query_words:
        return 0.0
    
    chunk_lower = chunk_text.lower()
    matches = sum(1 for w in query_words if w in chunk_lower)
    return matches / len(query_words)


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """
    Hybrid retrieval: FAISS semantic search + keyword boosting.
    
    1. Encode query, normalize, search FAISS (cosine similarity)
    2. Look up chunk metadata from SQLite
    3. Apply keyword boost to re-rank results
    4. Return top_k with proper confidence scores
    """
    # Safety: ensure query is always a string (guards against dict/list from LLM)
    if not isinstance(query, str):
        logger.warning("retrieve() got non-string query type=%s, converting: %s", type(query).__name__, str(query)[:100])
        query = str(query)

    index = load_index()
    if index is None or index.ntotal == 0:
        logger.warning("Empty or missing index. Call /sync first.")
        return []

    # Encode and normalize query
    query_vector = embedding_model.encode([query])
    query_vector = np.array(query_vector, dtype=np.float32)
    vector_store.normalize_L2(query_vector)

    # Search FAISS — get more than needed for re-ranking
    search_k = min(top_k * 8, index.ntotal)
    scores, indices = index.search(query_vector, search_k)

    # Filter valid results (-1 means no result)
    valid = [(int(idx), float(score)) for idx, score in zip(indices[0], scores[0]) if idx >= 0]
    if not valid:
        return []

    # Look up metadata from SQLite
    chunk_ids = [idx for idx, _ in valid]
    score_map = {idx: score for idx, score in valid}
    chunks = db.get_chunks_by_ids(chunk_ids)

    # Hybrid scoring: combine semantic + keyword
    results = []
    for chunk in chunks:
        cid = chunk["chunk_id"]
        semantic_score = score_map.get(cid, 0.0)  # Cosine sim: 0.0 to 1.0
        kw_score = keyword_score(query, chunk["text"])  # Keyword: 0.0 to 1.0
        
        # Hybrid: 70% semantic + 30% keyword
        hybrid_score = (0.7 * semantic_score) + (0.3 * kw_score)
        
        # Confidence as percentage (cosine similarity already in [0,1])
        chunk["distance"] = 1.0 - semantic_score  # For backward compatibility
        chunk["confidence"] = max(0, min(100, round(hybrid_score * 100, 1)))
        chunk["semantic_score"] = round(semantic_score * 100, 1)
        chunk["keyword_score"] = round(kw_score * 100, 1)
        results.append(chunk)

    # Sort by hybrid confidence (descending) — Stage 1 ranking
    results.sort(key=lambda x: x["confidence"], reverse=True)

    # ── Stage 2: Cross-Encoder Reranking ──
    # Take top candidates from Stage 1, re-score with cross-encoder for precision
    rerank_candidates = results[:top_k * 3]  # Rerank top 15 candidates
    if rerank_candidates:
        try:
            pairs = [[query, r["text"]] for r in rerank_candidates]
            ce_scores = reranker_model.predict(pairs)

            for i, r in enumerate(rerank_candidates):
                ce_score = float(ce_scores[i])
                # Normalize cross-encoder score (typically -10 to +10) to 0-1
                ce_normalized = max(0, min(1, (ce_score + 5) / 15))
                # Final score: 40% hybrid + 60% cross-encoder
                final_score = (0.4 * r["confidence"] / 100) + (0.6 * ce_normalized)
                r["confidence"] = max(0, min(100, round(final_score * 100, 1)))
                r["rerank_score"] = round(ce_normalized * 100, 1)

            # Re-sort by final confidence
            rerank_candidates.sort(key=lambda x: x["confidence"], reverse=True)
            logger.info("Cross-encoder reranked %d candidates", len(rerank_candidates))
        except Exception as e:
            logger.warning("Cross-encoder reranking failed, using hybrid scores: %s", e)

    results = rerank_candidates[:top_k]

    logger.info("Retrieved %d chunks for: '%s...'", len(results), query[:50])
    for r in results:
        logger.info("  -> %s (p.%d) conf=%d%% [sem=%d%% kw=%d%% rerank=%s%%]",
                     r["filename"], r["page_num"], r["confidence"],
                     r["semantic_score"], r["keyword_score"],
                     r.get("rerank_score", "N/A"))
    return results


def retrieve_for_document(query: str, filename: str, top_k: int = 5) -> list[dict]:
    """Retrieve chunks only from a specific document."""
    all_results = retrieve(query, top_k=top_k * 3)
    return [r for r in all_results if r["filename"] == filename][:top_k]


def retrieve_multi_query(queries: list[str], top_k: int = 3) -> list[dict]:
    """Retrieve chunks for multiple sub-queries. Deduplicates across queries."""
    seen_ids = set()
    all_results = []
    for query in queries:
        for r in retrieve(query, top_k=top_k):
            if r["chunk_id"] not in seen_ids:
                r["source_query"] = query
                all_results.append(r)
                seen_ids.add(r["chunk_id"])
    all_results.sort(key=lambda x: x["confidence"], reverse=True)
    return all_results
