import os
from dotenv import load_dotenv

load_dotenv()

# Groq provider settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

# OpenAI provider settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Active provider: "openai" or "groq"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_CONTEXT_DOCS = 5

os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
