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
MODEL = os.getenv("MODEL", "llama-3.1-8b-instant")

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

# --- Gemini Flash Client (lazy-loaded) — used for Compliance Agent (complex reasoning) ---
GCP_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gcp-key.json")
_gemini_flash_model = None

def get_gemini_flash():
    """Lazy-load Gemini 2.5 Flash for compliance reasoning. Avoids startup delay."""
    global _gemini_flash_model
    if _gemini_flash_model is None:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_KEY_PATH
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(
            GCP_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        import vertexai
        vertexai.init(project="ambitio-ds-v2", location="us-central1", credentials=credentials)
        from vertexai.generative_models import GenerativeModel
        _gemini_flash_model = GenerativeModel("gemini-2.5-flash")
        logger.info("Gemini 2.5 Flash loaded for compliance reasoning")
    return _gemini_flash_model

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
