"""
Continuous-RAG Configuration
Centralized configuration for all components - single source of truth.
"""
import os
import logging
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

load_dotenv()

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("continuous-rag")

# --- API Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("MODEL", "openai/gpt-oss-120b")

# --- Embedding Config ---
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# --- Chunking Config ---
CHUNK_SIZE = 600           # Target chars per chunk (sentence-aware, won't cut mid-sentence)
CHUNK_OVERLAP = 1          # Number of overlap sentences (not chars) for context continuity

# --- Paths (relative to project root, assumes running via uvicorn from root) ---
DOCUMENTS_DIR = os.path.join(".", "documents")
INDEX_DIR = os.path.join(".", "faiss_index")
INDEX_PATH = os.path.join(INDEX_DIR, "index.bin")
DB_PATH = os.path.join(".", "metadata.db")

# --- Groq Client (singleton) — used for Router, Q&A Retriever, Change Analyzer ---
groq_client = Groq(api_key=GROQ_API_KEY)

# NOTE: Compliance agent uses Groq (same as other agents).
# Gemini/GCP integration has been removed — no google-cloud packages required.

# --- Embedding Model (singleton - loaded once, used everywhere) ---
logger.info("Loading embedding model: %s ...", EMBEDDING_MODEL_NAME)
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
logger.info("Embedding model loaded successfully.")

# --- Cross-Encoder Reranker (for two-stage retrieval) ---
from sentence_transformers import CrossEncoder
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
logger.info("Loading cross-encoder reranker: %s ...", RERANKER_MODEL_NAME)
reranker_model = CrossEncoder(RERANKER_MODEL_NAME)
logger.info("Cross-encoder reranker loaded successfully.")
