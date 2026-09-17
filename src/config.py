import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]
DEFAULT_COLLECTION = os.getenv("DEFAULT_COLLECTION", "po_tud")
EMBEDDING_DIM = 768
