import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# LLM Providers
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip('"\'' )
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"\'' )
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip('"\'' )

# LangSmith Tracing
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "").strip('"\'' )
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "policy-rag-assistant")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT

# Local Retrieval & Storage Settings
STORAGE_DIR = BASE_DIR / os.getenv("STORAGE_DIR", "./storage")
POLICIES_DIR = BASE_DIR / "data" / "policies"
MANIFEST_PATH = BASE_DIR / "data" / "manifest.json"

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL", "ms-marco-TinyBERT-L-2-v2")
CALIBRATED_SUFFICIENCY_THRESHOLD = float(os.getenv("CALIBRATED_SUFFICIENCY_THRESHOLD", "0.03"))

# Retrieval hyperparameters
TOP_K_RETRIEVAL = 15
TOP_K_RERANKED = 4
RRF_K_CONSTANT = 60
MAX_PER_POLICY = 2
