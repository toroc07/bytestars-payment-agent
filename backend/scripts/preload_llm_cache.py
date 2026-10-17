"""Copies this machine's LLM readings of the dataset images into the database cache (table llm_cache).

The production backend then reads those images without calling Gemini (no quota, ~1 s instead of ~50 s).
Only readings of dataset images are copied; keys are the same hash production computes (prompt + file).

Usage (from backend/, with the production database in DATABASE_URL; nothing is printed about it):
    PowerShell:  $env:DATABASE_URL="<cadena de Neon>"; .venv\\Scripts\\python -m scripts.preload_llm_cache
"""

import json
import sys
from pathlib import Path

from app.agent.extraction import PROMPT, _document_block
from app.agent.pipeline import sniff_mime
from app.config import settings
from app.db.models import Base
from app.db.repositories import SqlLlmCacheRepository, SqlRuleSetRepository
from app.db.session import SessionLocal, engine
from app.llm import JsonCache, LLMRequest
from app.llm.chain import default_cache_folder

DATASET = Path(__file__).resolve().parents[2] / "dataset"


def main() -> int:
    if settings.DATABASE_URL.startswith("sqlite"):
        print("DATABASE_URL apunta a SQLite: pon la cadena de Neon en DATABASE_URL antes de ejecutar.")
        return 1
    folder = default_cache_folder()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    company = SqlRuleSetRepository(db).get_current().company_name  # the prompt names the company: keys depend on it
    system = PROMPT.format(company_name=company)
    cases = json.loads((DATASET / "expected.json").read_text(encoding="utf-8"))["invoices"]
    cache = SqlLlmCacheRepository(db)
    copied = missing = present = 0
    for case in cases:
        if case["format"] != "image":
            continue
        data = (DATASET / case["file"]).read_bytes()
        request = LLMRequest(system=system, text=_document_block("", ""), file_bytes=data, mime_type=sniff_mime(data))
        key = JsonCache.key(request)
        local = folder / f"{key}.json"
        if cache.get(key) is not None:
            present += 1
        elif local.exists():
            cache.put(key, json.loads(local.read_text(encoding="utf-8")))
            copied += 1
        else:
            missing += 1
            print(f"  sin lectura local: {case['file']}")
    db.close()
    print(f"Imágenes del dataset: {copied} copiadas, {present} ya estaban, {missing} sin lectura local.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
