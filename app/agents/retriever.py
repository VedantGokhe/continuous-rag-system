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
- Be concise and direct
- Cite the source document and page when possible (e.g., "According to HR_Policy.pdf, page 3...")
- If the context doesn't contain enough information, say "I don't have enough information in the indexed documents to answer this."
- Do NOT make up information

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
