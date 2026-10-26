"""Configuration settings for English to SQL Generator."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Load .env file
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Provider & Model Settings
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "groq").lower()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))

# Database & Security
EXECUTION_TIMEOUT_SECONDS = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "10"))
MAX_RESULT_ROWS = int(os.getenv("MAX_RESULT_ROWS", "500"))
READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "true").lower() in ("true", "1", "yes")

# Default Sample Database Path
DEFAULT_DB_PATH = DATA_DIR / "sample_enterprise.db"
