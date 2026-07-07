# 🧠 Continuous-RAG: Enterprise Policy Intelligence System

> **Production-grade multi-agent RAG system** with continuous document ingestion, compliance checking, RAG evaluation pipeline, and hybrid LLM architecture — powered by LangGraph, FAISS, Groq, and Google Gemini.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agents-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Pro+Flash-4285F4.svg)](https://ai.google.dev/)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.1-red.svg)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Problem Statement

Large enterprises store hundreds of internal policy documents in PDF format. Employees struggle to quickly retrieve accurate, version-consistent information. Traditional keyword search retrieves irrelevant or outdated sections.

**This system solves three problems at once:**
1. **Q&A** — Instant answers from the latest policy documents with page-level citations
2. **Compliance Checking** — Multi-document reasoning to verify if an action complies with company policies (ALLOWED / DENIED / CONDITIONAL)
3. **Change Impact Analysis** — Automatic detection of what changed when documents are updated, who is affected, and policy conflicts

---

## 🚀 Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **Multi-Agent AI** | LangGraph workflow: Router → Retriever / Compliance / Change Analyzer → Synthesizer |
| 🧪 **RAG Evaluation Pipeline** | Automated quality scoring with Gemini 2.5 Pro as judge — faithfulness, relevancy, correctness, hallucination |
| 🔀 **Hybrid LLM Architecture** | Groq (fast Q&A, ~1s) + Gemini Flash (compliance reasoning) + Gemini Pro (evaluation judge) |
| 🔍 **3-Stage Retrieval** | FAISS semantic search → Keyword boosting → Cross-encoder reranking (ms-marco-MiniLM-L6-v2) |
| 🔄 **Continuous Ingestion** | Watchdog file watcher auto-detects new/modified/deleted PDFs — no manual triggers needed |
| 🔐 **Hash-Based Change Detection** | SHA-256 hashing skips unchanged files — only processes what's new or modified |
| 📊 **Incremental FAISS Indexing** | IndexIDMap for add/remove operations without full index rebuilds |
| ✅ **Compliance Verdicts** | Decomposes queries, searches across multiple policies, detects conflicts, returns ALLOWED/DENIED/CONDITIONAL |
| 💬 **Conversation Memory** | LLM-powered query rewriting for natural follow-up conversations |
| 📋 **Change Impact Reports** | LLM-powered diff analysis on document updates — severity, affected parties, conflicts |
| 📄 **Page-Level Citations** | Every answer includes exact document name, page number, and version |
| 🎯 **Agent Trace** | Full observability — see every step the agent pipeline takes |
| 🖥️ **React Dark Mode UI** | 3-panel dashboard with document viewer, markdown rendering, and eval report modal |

---

## 🏗️ System Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │           REACT FRONTEND (3-Panel)          │
                         │  Sidebar │ Chat Panel │ Sources + Trace     │
                         └────────────────┬────────────────────────────┘
                                          │ HTTP API
                         ┌────────────────┴────────────────────────────┐
                         │              FastAPI Backend                 │
                         │  /upload /sync /query /eval /status /history│
                         └────────────────┬────────────────────────────┘
                                          │
          ┌───────────────────────────────┼──────────────────────────────┐
          │                               │                              │
          ▼                               ▼                              ▼
┌──────────────────┐          ┌──────────────────┐           ┌──────────────────┐
│  FILE WATCHER    │          │  AGENT PIPELINE  │           │  INGESTION       │
│  (watchdog)      │          │  (LangGraph)     │           │  ENGINE          │
│                  │          │                  │           │                  │
│  Monitors docs/  │          │  ┌────────────┐  │           │  PDF → Sentences │
│  folder for      │────────▶ │  │   Router   │  │           │  → Embeddings    │
│  CREATE/MODIFY/  │          │  │  (Groq)    │  │           │  → FAISS Index   │
│  DELETE events   │          │  └─────┬──────┘  │           │                  │
│                  │          │    ┌───┴───┐     │           │  Sentence-aware  │
│  Debounced       │          │    ▼   ▼   ▼     │           │  chunking +      │
│  auto-sync       │          │  [R] [C] [CA]    │           │  text cleaning   │
└──────────────────┘          │    └───┬───┘     │           └──────────────────┘
                              │  ┌─────▼──────┐  │
                              │  │Synthesizer │  │           ┌──────────────────┐
                              │  └────────────┘  │           │  EVALUATION      │
                              └──────────────────┘           │  PIPELINE        │
                                                             │                  │
       [R]  = Retriever (Groq ~1s)                           │  Gemini 2.5 Pro  │
       [C]  = Compliance (Gemini Flash ~10s)                 │  as Judge        │
       [CA] = Change Analyzer (Groq)                         │  6 test cases    │
                                                             └──────────────────┘
```

### Hybrid LLM Strategy

| Component | Model | Why |
|-----------|-------|-----|
| **Router** | Groq (Llama 3.1 8B) | Ultra-fast intent classification (~200ms) |
| **Q&A Retriever** | Groq (Llama 3.1 8B) | Fast answer generation (~300ms) |
| **Compliance Agent** | Gemini 2.5 Flash | Superior reasoning for multi-document analysis |
| **Evaluation Judge** | Gemini 2.5 Pro | Most accurate scoring for RAG metrics |
| **Change Analyzer** | Groq (Llama 3.1 8B) | Fast structured diff analysis |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + TypeScript + Tailwind CSS + Vite |
| **Backend** | FastAPI + Uvicorn |
| **AI Agents** | LangGraph (StateGraph with conditional routing) |
| **Vector DB** | FAISS (IndexFlatIP + IndexIDMap for cosine similarity) |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2, 384-dim) |
| **Reranker** | Cross-Encoder (ms-marco-MiniLM-L-6-v2) |
| **LLM (Fast)** | Groq API (Llama 3.1 8B Instant) |
| **LLM (Smart)** | Google Gemini 2.5 Flash + Pro |
| **Metadata DB** | SQLite3 (WAL mode) |
| **PDF Processing** | PyPDF + sentence-aware chunking |
| **File Watching** | Watchdog (debounced auto-sync) |
| **Containerization** | Docker + Docker Compose |

---

## 🧪 RAG Evaluation Pipeline

Built-in evaluation system that runs your RAG pipeline against a golden test set, then uses **Gemini 2.5 Pro as an impartial judge** to score each answer.

### Metrics Scored
| Metric | Description | Industry Benchmark |
|--------|-------------|-------------------|
| **Faithfulness** | Is the answer grounded in retrieved sources? | 70-90% |
| **Relevancy** | Does the answer address the question? | 80-95% |
| **Correctness** | Does it match the expected answer? | 60-85% |
| **Hallucination** | Did the AI add false information? (lower = better) | 5-20% |

### Our Results
```
┌─────────────────────────────────────────────────┐
│  Overall: 79%  │  Faithfulness: 78%             │
│  Relevancy: 92% │  Hallucination: 20%            │
│  Source Accuracy: 100%                           │
└─────────────────────────────────────────────────┘
```

### Test Set (2 Core + 4 Challenging)
| Query | Type | Expected Score |
|-------|------|---------------|
| Password length required? | Core Q&A | ~100% |
| Work remotely from Dubai? | Core Compliance | ~100% |
| Expense a standing desk? | Inference (not in policy) | ~0-50% |
| Unauthorized AI data sharing? | Consequences query | ~50-80% |
| Work remotely from Germany? | Multi-hop reasoning | ~50-100% |
| Home office allowance? | Core Q&A | ~100% |

---

## 🔍 3-Stage Retrieval Pipeline

```
Query → Embedding (all-MiniLM-L6-v2)
  │
  ├── Stage 1: FAISS Semantic Search (cosine similarity, top_k×8 candidates)
  │
  ├── Stage 2: Keyword Boosting (30% weight for exact term matches)
  │     Hybrid Score = 0.7 × semantic + 0.3 × keyword
  │
  └── Stage 3: Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)
        Final top_k results with reranked confidence scores
```

**Why 3 stages?** Semantic search misses exact term matches (e.g., "ChatGPT"). Keyword boosting catches these. Cross-encoder reranking provides the highest quality ordering.

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- [Groq API key](https://console.groq.com/)
- Google Cloud service account with Gemini API access (for evaluation + compliance)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/VedantGokhe/continuous-rag-system.git
cd continuous-rag-system

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Create .env file
echo GROQ_API_KEY=your_groq_api_key_here > .env
echo MODEL=llama-3.1-8b-instant >> .env
```

Place your Google Cloud service account key as `gcp-key.json` in the project root (required for Gemini evaluation and compliance).

### 3. Setup Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Create Documents Folder & Load Sample PDFs

```bash
mkdir documents

# Copy the included sample policy documents
copy sample_docs\* documents\        # Windows
# cp sample_docs/* documents/        # Mac/Linux
```

> 📁 The `sample_docs/` folder contains 4 pre-built enterprise policy PDFs for testing:
> - `HR_Policy.pdf` — Leave, remote work, employee guidelines
> - `Finance_Guidelines.pdf` — Expense limits, travel budgets, allowances
> - `IT_Security_Policy.pdf` — Password rules, AI tool usage, data handling
> - `Travel_and_Remote_Work_Abroad.pdf` — International remote work, country tiers, approvals
>
> These PDFs are generated by `generate_test_pdfs.py` and cover realistic enterprise scenarios.

---

## 🚦 Running the System

### Start Backend (Terminal 1)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Start Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

### Open the App
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Or use Docker
```bash
docker-compose up --build
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check + API overview |
| `POST` | `/upload` | Upload a PDF document |
| `GET` | `/sync` | Trigger incremental document sync |
| `POST` | `/query` | Query with chat history (conversation memory) |
| `GET` | `/query?q=...` | Simple query via multi-agent pipeline |
| `GET` | `/eval` | Run RAG evaluation (6 tests, Gemini Pro judge) |
| `GET` | `/status` | System status + indexed documents |
| `GET` | `/history` | Query history with answers |
| `GET` | `/changes` | Document change reports |
| `GET` | `/document/{filename}` | Get full document text |

### Try These Queries in the UI

Open http://localhost:5173 and type these in the chat:

| Query | Expected Result |
|-------|----------------|
| `How many sick days do employees get per year?` | **Q&A** → "12 days" from HR_Policy.pdf |
| `What is the home office setup allowance?` | **Q&A** → "$500 one-time" from Finance_Guidelines.pdf |
| `Can I work remotely from Dubai for 2 months?` | **Compliance** → ❌ DENIED (UAE is Tier 3) |
| `Am I allowed to use ChatGPT for my work tasks?` | **Compliance** → ❌ DENIED (Prohibited) |
| `How long can I work remotely from Germany?` | **Compliance** → ✅ CONDITIONAL (Tier 1, 30 days max) |
| `Which are the tier 1 countries to work from?` | **Compliance** → ✅ ALLOWED (UK, Canada, Germany, Australia, Singapore, Japan) |
| `What changed in the latest policy update?` | **Changes** → Shows diff report if documents were updated |

> 💡 **Tip:** Click on any assistant message to see its sources, findings, and agent trace in the right panel.

---

## 🤖 Agent Architecture (LangGraph)

### Router Agent
Classifies every query into one of three intents using Groq LLM:
- `"question"` → Standard RAG retrieval
- `"compliance"` → Multi-document compliance reasoning  
- `"what_changed"` → Document change analysis

Includes **query rewriting** for conversation memory — vague follow-ups like "2 days?" get rewritten to standalone questions using the last 4 messages as context.

### Retriever Agent
3-stage retrieval pipeline: FAISS semantic search → keyword boosting → cross-encoder reranking → Groq LLM generation with page-level citations.

### Compliance Agent
1. **Decompose** query into 2-4 sub-questions targeting different policy areas (Gemini Flash)
2. **Multi-query retrieval** across all documents with cross-encoder reranking
3. **Cross-document reasoning** via Gemini Flash — finds conflicts between policies
4. **DENIED-first logic** — checks for hard prohibitions (Tier 3 countries, prohibited tools) before considering conditions
5. **Programmatic post-check** — overrides CONDITIONAL → DENIED when prohibition keywords found in context
6. **Verdict**: ALLOWED / DENIED / CONDITIONAL with conditions list

### Change Analyzer Agent
1. Checks for stored change reports (auto-generated on document update)
2. Presents structured analysis: what changed, severity, who's affected
3. Cross-references against other policies for conflicts

### Synthesizer Agent
Final node — formats response, calculates confidence (MAX of top-2 chunks), saves to query history.

---

## 📂 Project Structure

```
continuous-rag/
├── app/
│   ├── __init__.py
│   ├── config.py              # Config + Groq client + Gemini Flash lazy loader
│   ├── database.py            # SQLite with documents, chunks, history, changes
│   ├── ingestion.py           # Sentence-aware chunking + hash-based FAISS indexing
│   ├── retrieval.py           # 3-stage retrieval: semantic + keyword + reranker
│   ├── evaluation.py          # RAG eval pipeline with Gemini Pro judge
│   ├── watcher.py             # Watchdog file watcher for continuous sync
│   ├── main.py                # FastAPI app with all endpoints
│   └── agents/
│       ├── __init__.py
│       ├── state.py           # Shared TypedDict state for LangGraph
│       ├── router.py          # Intent classification + query rewriting
│       ├── retriever.py       # Q&A agent with cross-encoder reranking
│       ├── compliance.py      # Multi-doc compliance (Gemini Flash + post-check)
│       ├── change_analyzer.py # Document change impact analyzer
│       ├── synthesizer.py     # Response formatting + history
│       └── graph.py           # LangGraph workflow definition
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # 3-panel layout with dark mode
│   │   ├── api.ts             # API client with chat history
│   │   ├── types.ts           # TypeScript interfaces
│   │   └── components/
│   │       ├── Header.tsx     # Status bar + Live indicator + Eval button
│   │       ├── Sidebar.tsx    # Document list + upload + drag-drop + viewer modal
│   │       ├── ChatPanel.tsx  # Chat with markdown rendering + click-to-update
│   │       └── SourcesPanel.tsx # Citations + compliance panel + agent trace
│   ├── package.json
│   └── vite.config.ts
│
├── documents/                 # PDF storage (auto-watched)
├── faiss_index/               # FAISS vector index (persistent)
├── gcp-key.json               # Google Cloud service account (not in git)
├── .env                       # API keys (GROQ_API_KEY)
├── requirements.txt
├── generate_test_pdfs.py      # Script to generate sample policy PDFs
├── test_queries.txt           # Evaluation test queries with results
├── stage1_findings.txt        # Testing findings and fix log
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🎯 Design Decisions

### Why Hybrid LLM Architecture?
| Decision | Reasoning |
|----------|-----------|
| Groq for Q&A | ~1s latency, sufficient for factual retrieval |
| Gemini Flash for Compliance | Superior reasoning for multi-document analysis, handles complex JSON output |
| Gemini Pro for Evaluation | Most accurate judge model, used only for offline evaluation |
| Not using RAGAS library | Custom evaluation gives full control over metrics and prompts |

### Why 3-Stage Retrieval?
Semantic search alone misses exact term matches (e.g., "ChatGPT", "Dubai"). Adding keyword boosting catches these. Cross-encoder reranking provides production-quality ordering with ~2x accuracy improvement over FAISS alone.

### Why Programmatic Post-Check for Compliance?
LLMs are non-deterministic. Even with perfect prompts, Gemini Flash sometimes gives CONDITIONAL instead of DENIED for prohibited items. The post-check scans retrieved context for prohibition keywords and overrides the verdict deterministically — "belt and suspenders" approach.

### Why Hash-Based Incremental Indexing?
Full index rebuilds don't scale. SHA-256 hash comparison means:
- Upload 100 documents, modify 1 → only 1 gets re-processed
- FAISS IndexIDMap supports `add_with_ids()` and `remove_ids()` for surgical updates

### Why Sentence-Aware Chunking?
Character-based chunking cuts mid-sentence, breaking semantic meaning. Sentence-aware chunking respects sentence boundaries using regex — chunks never cut mid-thought.

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| **Q&A Latency** | ~1-2s (Groq) |
| **Compliance Latency** | ~10-15s (Gemini Flash) |
| **Evaluation (6 tests)** | ~3 min (Gemini Pro judge) |
| **FAISS Search** | <10ms for 10K+ vectors |
| **Cross-Encoder Rerank** | ~300ms for 15 candidates |
| **Incremental Sync** | ~2-5s per document |
| **Hash Check** | <1ms per file |

### RAG Evaluation Scores (Industry Benchmarks)

| Metric | Our Score | Industry Benchmark |
|--------|-----------|-------------------|
| **Overall** | 79% | 70-85% ✅ |
| **Faithfulness** | 78% | 70-90% ✅ |
| **Relevancy** | 92% | 80-95% ✅ |
| **Hallucination** | 20% | 5-20% ✅ |
| **Source Accuracy** | 100% | 80-95% ✅ |

---

## 🐛 Testing & Iteration Log

The system went through systematic testing documented in `stage1_findings.txt`:

| Stage | Issues Found | Issues Fixed |
|-------|-------------|-------------|
| Stage 1 v1 | 11 issues (FAISS miss, no memory, confidence bugs) | All 11 fixed |
| Stage 1 v2 | 5 new issues (JSON errors, panel sync, confidence formula) | All 5 fixed |
| Stage 2 | Evaluation pipeline (expired models, dict errors, verdict issues) | All fixed |

Key fixes: sentence-aware chunking, hybrid retrieval, cross-encoder reranking, conversation memory, compliance post-check, Gemini hybrid architecture.

---

## 👤 Author

**Vedant Gokhe**
- GitHub: [VedantGokhe](https://github.com/VedantGokhe)
- LinkedIn: [vedantgokhe](https://www.linkedin.com/in/vedantgokhe/)
- Email: vedantgokheofficial@gmail.com

---

## 📚 References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FAISS — Facebook AI Similarity Search](https://faiss.ai/)
- [Sentence-BERT (SBERT)](https://arxiv.org/abs/1908.10084)
- [RAG Paper — Lewis et al., 2020](https://arxiv.org/abs/2005.11401)
- [Cross-Encoders for Reranking](https://www.sbert.net/examples/applications/cross-encoder/README.html)
- [Google Gemini API](https://ai.google.dev/gemini-api/docs)
- [Groq API Documentation](https://console.groq.com/docs)

---

<div align="center">
<b>⭐ Star this repo if you find it useful!</b>
<br/>
Built with ❤️ for enterprise document intelligence
</div>
