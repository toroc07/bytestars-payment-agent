import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


def main() -> None:
    openapi_schema = app.openapi()
    out_path = REPO_ROOT / "contracts" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(openapi_schema, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported OpenAPI schema to {out_path}")


if __name__ == "__main__":
    main()
