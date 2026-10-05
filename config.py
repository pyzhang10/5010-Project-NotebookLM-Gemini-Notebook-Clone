from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("APP_DATA_DIR", BASE_DIR / "data"))
NOTEBOOKS_DIR = DATA_DIR / "notebooks"
NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
LLM_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "4"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
