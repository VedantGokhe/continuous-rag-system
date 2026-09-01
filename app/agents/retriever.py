"""
Retriever Agent
Handles basic Q&A queries — retrieves relevant chunks and generates an answer.
This is the standard RAG pipeline path.
"""
from app.config import groq_client, MODEL, logger
from app.retrieval import retrieve
from app.agents.state import AgentState


QA_PROMPT = """You are a helpful enterprise assistant. Answer the question based ONLY on the context below.

Rules:
- Be concise, direct, and complete. State all specific facts, numbers, and limits in plain text.
- Do NOT use bracket citations like 【...】 or inline file tags like (filename.pdf, page X). Write clean natural prose.
- If the context doesn't contain enough information, say "I don't have enough information in the indexed documents to answer this."
- Do NOT make up information.

Context:
{context}

Question: {query}

Answer:"""


def retriever_node(state: AgentState) -> AgentState:
    """
    Standard RAG retrieval + LLM generation.
    1. Retrieve relevant chunks from FAISS
    2. Build context from chunks
    3. Generate answer via Groq LLM
    """
    query = state["query"]
    trace = state.get("agent_trace", [])
    trace.append("RETRIEVER: Searching FAISS index...")

    # Step 1: Retrieve chunks
    chunks = retrieve(query, top_k=5)
    trace.append(f"RETRIEVER: Found {len(chunks)} relevant chunks")

    if not chunks:
        return {
            **state,
            "retrieved_chunks": [],
            "final_answer": "No relevant documents found. Please upload documents and sync the index.",
            "sources": [],
            "confidence": 0.0,
            "agent_trace": trace,
        }

    # Step 2: Build context
    context_parts = []
    for c in chunks:
        source_info = f"[Source: {c['filename']}, Page {c['page_num']}, v{c['version']}]"
        context_parts.append(f"{source_info}\n{c['text']}")
    
    context_text = "\n\n---\n\n".join(context_parts)

    # Step 3: Generate answer
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": QA_PROMPT.format(context=context_text, query=query)
            }],
            temperature=0.2,
            max_tokens=600,
        )
        answer = response.choices[0].message.content.strip()
        import re
        # STEP 1: Normalize ALL unicode spaces → ASCII space
        answer = re.sub(r'[\u00a0\u202f\u2000-\u200b\u3000]+', ' ', answer)
        # STEP 2: Normalize ALL unicode dashes → ASCII hyphen
        answer = re.sub(r'[\u2011\u2012\u2013\u2014\u2015\u2212]', '-', answer)
        # STEP 3: Smart bracket extractor 【value - source】
        def _extract_bracket(m):
            inner = m.group(1).strip()
            match = re.search(r'^(.*?)\s*[\u2011-\u2015\u2212\-,;]\s*[A-Za-z0-9_\-]+\.pdf.*$', inner, flags=re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if val and not val.lower().endswith('.pdf'):
                    return val
            if re.match(r'^[A-Za-z0-9_\-]+\.pdf', inner, flags=re.IGNORECASE):
                return ''
            return inner
        answer = re.sub(r'\u3010(.*?)\u3011', _extract_bracket, answer)
        # STEP 4: Strip parenthetical PDF citations
        answer = re.sub(r'\s*\([^)]{0,80}\.pdf[^)]*\)', '', answer)
        # STEP 5: Collapse multiple spaces
        answer = re.sub(r'[ \t]{2,}', ' ', answer).strip()
        trace.append("RETRIEVER: Generated answer via LLM")
    except Exception as e:
        logger.error("LLM generation failed: %s", e)
        answer = f"Error generating answer: {str(e)}"
        trace.append(f"RETRIEVER: LLM error - {str(e)[:50]}")

    # Confidence = MAX of top-2 chunks (Fix #16: not average of all 5)
    sorted_conf = sorted([c.get("confidence", 0) for c in chunks], reverse=True)
    avg_confidence = max(sorted_conf[:2]) if sorted_conf else 0

    sources = [
        {
            "filename": c["filename"],
            "page_num": c["page_num"],
            "version": c["version"],
            "confidence": c.get("confidence", 0),
            "preview": c["text"][:100] + "...",
        }
        for c in chunks
    ]

    return {
        **state,
        "retrieved_chunks": chunks,
        "final_answer": answer,
        "sources": sources,
        "confidence": avg_confidence,
        "agent_trace": trace,
    }
