"""Higiene do repositorio: sem segredos versionados, .env ignorado, docs de operacao em dia com a API e as migracoes."""
import re
import subprocess
from pathlib import Path

import pytest

from src.api.main import app

ROOT = Path(__file__).resolve().parents[1]
OPS_DOC = ROOT / "docs" / "03-arquitetura" / "operacao.md"
TEXT_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".sql", ".sh", ".ps1", ".json", ".ts", ".tsx", ".toml", ".txt", ".example", ".cfg", ".ini"}
PLACEHOLDER = re.compile(r"troque|change|example|placeholder", re.I)
SKIP = {"frontend/package-lock.json", "frontend/openapi.json"}


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git indisponivel")
    return [ROOT / f for f in out if f not in SKIP and ((ROOT / f).suffix in TEXT_SUFFIXES or f.endswith(".env.example")) and (ROOT / f).is_file()]


def test_env_file_is_not_tracked_and_is_ignored():
    names = {p.name for p in tracked_files()}
    assert ".env" not in names
    assert ".env" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_no_private_keys_or_real_jwts_in_tracked_files():
    patterns = [re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}")]
    hits = [f"{p.relative_to(ROOT)}: {rx.pattern[:20]}" for p in tracked_files() for rx in patterns if rx.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert hits == []


def test_no_dsn_with_real_looking_password_in_tracked_files():
    dsn = re.compile(r"postgres(?:ql)?://[^:\s/@]+:([^@\s]+)@")
    allowed = {"postgres", "change-me", "changeme", "senha", "password", "ownerpw", "ropw", "etlpw", "auditpw", "etl", "api", "audit", "user", "pass"}
    hits = []
    for p in tracked_files():
        for m in dsn.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            pw = m.group(1)
            if not (pw in allowed or pw.startswith(("$", "{", "<", "%")) or PLACEHOLDER.search(pw) or "example" in pw.lower()):
                hits.append(f"{p.relative_to(ROOT)}: {pw[:3]}***")
    assert hits == []


def test_env_example_has_no_filled_secrets():
    secret_keys = re.compile(r"^(JWT_SECRET|POSTGRES_\w*PASSWORD|DATABASE_URL\w*)=(.*)$")
    filled = []
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        m = secret_keys.match(line.strip())
        if m and m.group(2).strip() and not PLACEHOLDER.search(m.group(2)) and "<" not in m.group(2) and "://" not in m.group(2):
            filled.append(m.group(1))
    assert filled == []


def test_operations_doc_covers_every_endpoint():
    doc = OPS_DOC.read_text(encoding="utf-8")
    missing = [p for p in app.openapi()["paths"] if p not in doc]
    assert missing == []


def test_operations_doc_lists_every_migration():
    doc = OPS_DOC.read_text(encoding="utf-8")
    missing = [m.name for m in sorted((ROOT / "db" / "migrations").glob("*.sql")) if m.name not in doc]
    assert missing == []


def test_operations_doc_mentions_each_env_variable_used_by_the_api():
    doc = OPS_DOC.read_text(encoding="utf-8")
    for var in ("JWT_SECRET", "DATABASE_URL_RO", "DATABASE_URL_AUDIT", "DATABASE_URL_ETL", "RATE_LIMIT_PER_MINUTE", "RATE_LIMIT_WRITE_PER_MINUTE", "CORS_ORIGINS"):
        assert var in doc, var
