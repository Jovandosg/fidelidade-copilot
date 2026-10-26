"""Exporta o OpenAPI da API (sem precisar de banco) para frontend/openapi.json.

Uso:  python scripts/export_openapi.py [--check]
Os tipos TypeScript sao gerados a partir deste arquivo (veja scripts/gen_types.ps1 / README).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from src.api.main import app  # noqa: E402

TARGET = ROOT / "frontend" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        current = TARGET.read_text(encoding="utf-8").replace("\r\n", "\n") if TARGET.exists() else ""
        sys.exit(0 if current == text else "openapi.json desatualizado: rode python scripts/export_openapi.py")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"escrito {TARGET}")
