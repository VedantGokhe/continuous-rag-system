"""
Continuous-RAG Agent State
Shared state definition for the LangGraph multi-agent workflow.
All agents read from and write to this state.
"""
from typing import TypedDict, Literal, Optional


class AgentState(TypedDict, total=False):
    """
    Shared state passed between all agents in the LangGraph workflow.
    
    Flow:
    User Query → Router → [Retriever | Compliance | ChangeAnalyzer] → Synthesizer → Response
    """

    # --- Input ---
    query: str                          # Original user query (may be rewritten)
    original_query: str                 # Raw query from user (before rewriting)
    chat_history: list[dict]            # Previous messages [{role, content}]
    
    # --- Router Output ---
    intent: Literal[                     # Classified intent
        "question",                      # Basic Q&A retrieval
        "compliance",                    # Multi-doc compliance check
        "what_changed",                  # Document change analysis
    ]
    intent_reasoning: str               # Why router chose this intent

    # --- Retriever Output ---
    retrieved_chunks: list[dict]        # Chunks from FAISS search
    
    # --- Compliance Agent Output ---
    sub_questions: list[str]            # Decomposed sub-questions
    findings: list[dict]                # Findings from each sub-question
    conflicts: list[dict]               # Cross-document conflicts
    verdict: str                        # ALLOWED / DENIED / CONDITIONAL
    conditions: list[str]               # Conditions if CONDITIONAL

    # --- Change Analyzer Output ---
    change_report: Optional[dict]       # Full change impact report

    # --- Synthesizer Output ---
    final_answer: str                   # Final synthesized answer
    sources: list[dict]                 # Source citations
    confidence: float                   # Overall confidence score (0-100)
    
    # --- Observability ---
    agent_trace: list[str]             # Step-by-step trace of agent actions
