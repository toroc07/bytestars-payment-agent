"""Vercel build step (pyproject.toml → [tool.vercel.scripts] build).

Only backend/ is deployed, but the fictional company lives in ../dataset/company.json. Copy it into
backend/seed_data/ so /api/dev/seed and /api/dev/reset can load it. Fails the build if it is missing:
a deploy that cannot seed the demo is worse than no deploy.
"""

import json
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SOURCE = BACKEND.parent / "dataset" / "company.json"
TARGET = BACKEND / "seed_data" / "company.json"


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: {SOURCE} not found. Enable 'Include files outside the root directory' in Vercel.")
        return 1
    json.loads(SOURCE.read_text(encoding="utf-8"))  # a broken file should fail here, not at the first reset
    TARGET.parent.mkdir(exist_ok=True)
    shutil.copyfile(SOURCE, TARGET)
    print(f"Copied {SOURCE.name} to {TARGET.relative_to(BACKEND)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
