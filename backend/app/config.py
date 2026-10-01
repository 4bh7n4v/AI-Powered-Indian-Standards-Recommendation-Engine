import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("ISRE_DATA_DIR", BASE_DIR / "data"))
VAR_DIR = Path(os.getenv("ISRE_VAR_DIR", BASE_DIR / "var"))
FRONTEND_DIST = Path(os.getenv("ISRE_FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"))
LOG_DIR = Path(os.getenv("ISRE_LOG_DIR", BASE_DIR.parent / "logs"))
LOG_LEVEL = os.getenv("ISRE_LOG_LEVEL", "INFO").upper()
LOG_RETENTION_DAYS = int(os.getenv("ISRE_LOG_RETENTION_DAYS", "30"))

# Dense retrieval: "auto" uses BGE-M3 when sentence-transformers is installed.
DENSE_MODE = os.getenv("ISRE_DENSE", "auto")  # auto | off
EMBED_MODEL = os.getenv("ISRE_EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("ISRE_RERANK_MODEL", "")  # e.g. BAAI/bge-reranker-v2-m3
# Optional LLM attribute extraction through a local Ollama server.
OLLAMA_MODEL = os.getenv("ISRE_OLLAMA_MODEL", "")  # e.g. qwen2.5:7b-instruct
OLLAMA_URL = os.getenv("ISRE_OLLAMA_URL", "http://localhost:11434")

# Below this confidence the engine abstains instead of guessing.
ABSTAIN_THRESHOLD = float(os.getenv("ISRE_ABSTAIN_THRESHOLD", "0.30"))
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
