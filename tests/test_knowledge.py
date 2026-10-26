"""Base de conhecimento do RAG: chunking, embeddings, validacao de fontes (sem banco) e ingestao/busca/versionamento (com pgvector)."""
import math
import os
import uuid
from datetime import date, timedelta

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from src import db
from src.knowledge.chunking import chunk_markdown
from src.knowledge.embeddings import DIM, HashingEmbedder, tokenize
from src.knowledge.ingest import SOURCES_DIR, SourceError, ingest_directory, parse_source
from src.knowledge.search import search_rules

DSN, DSN_ETL, DSN_RO = (os.environ.get(v) for v in ("DATABASE_URL", "DATABASE_URL_ETL", "DATABASE_URL_RO"))
needs_db = pytest.mark.skipif(not (DSN and DSN_ETL and DSN_RO), reason="DATABASE_URL, _ETL e _RO nao definidos")


def write(tmp_path, name="fonte.md", url="https://www.voeazul.com.br/br/pt/programa-fidelidade/niveis", consulted="2026-10-14", body="# Niveis\n\nTexto publico da regra."):
    path = tmp_path / name
    path.write_text(f"---\nurl: {url}\ntitle: Titulo\npublisher: Azul\nconsulted_at: {consulted}\n---\n{body}\n", encoding="utf-8")
    return path


# ---------- sem banco ----------
def test_embedding_is_deterministic_normalized_and_accent_insensitive():
    e = HashingEmbedder()
    a, b = e.embed("Níveis do programa de fidelidade"), e.embed("niveis do programa de fidelidade")
    assert len(a) == DIM and a == b and math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-9)
    assert e.embed("") == [0.0] * DIM and tokenize("Diamante Unique!") == ["diamante", "unique"]


def test_similar_text_is_closer_than_unrelated_text():
    e = HashingEmbedder()
    dot = lambda x, y: sum(p * q for p, q in zip(x, y))  # noqa: E731
    q = e.embed("quais sao os niveis do programa")
    assert dot(q, e.embed("O programa tem cinco niveis publicos")) > dot(q, e.embed("Tarifas aereas por rota e sazonalidade"))


def test_chunking_keeps_sections_and_limits_size():
    body = "# A\n\n" + "Frase longa de regra publica. " * 60 + "\n\n# B\n\nCurto.\n\nOutro paragrafo."
    chunks = chunk_markdown(body, max_chars=200)
    assert all(0 < len(c["content"]) <= 200 for c in chunks)
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
    assert {c["section"] for c in chunks} == {"A", "B"}
    assert [c["content"] for c in chunks if c["section"] == "B"] == ["Curto.\n\nOutro paragrafo."]
    assert chunk_markdown("   \n\n  ") == []


def test_seed_sources_are_valid_public_and_have_consultation_date():
    files = sorted(p for p in SOURCES_DIR.glob("*.md") if not p.name.startswith("_"))
    assert files
    for path in files:
        src = parse_source(path)
        assert src.url.startswith("https://www.voeazul.com.br/") and src.consulted_at <= date.today() and chunk_markdown(src.body)


@pytest.mark.parametrize("kwargs, message", [
    ({"url": "http://www.voeazul.com.br/x"}, "https"),
    ({"url": "https://evil.example.com/voeazul.com.br"}, "dominio"),
    ({"url": "https://voeazul.com.br.evil.com/x"}, "dominio"),
    ({"consulted": "14/10/2026"}, "consulted_at"),
    ({"consulted": (date.today() + timedelta(days=1)).isoformat()}, "futuro"),
    ({"body": ""}, "corpo"),
    ({"body": "Fale com maria@example.com"}, "PII"),
    ({"body": "CPF 123.456.789-09 do cliente"}, "PII"),
    ({"body": "Ligue (11) 91234-5678"}, "PII"),
])
def test_invalid_sources_are_rejected(tmp_path, kwargs, message):
    with pytest.raises(SourceError, match=message):
        parse_source(write(tmp_path, **kwargs))


def test_front_matter_is_required(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("sem front matter", encoding="utf-8")
    with pytest.raises(SourceError, match="front-matter"):
        parse_source(p)
    p.write_text("---\nurl: https://www.voeazul.com.br/x\n---\ncorpo", encoding="utf-8")
    with pytest.raises(SourceError, match="obrigatorios"):
        parse_source(p)


# ---------- com banco (imagem pgvector/pgvector:pg16) ----------
@pytest.fixture(scope="module")
def kb():
    name = f"fidelidade_kb_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    with psycopg.connect(make_conninfo(DSN, dbname=name)) as owner:
        db.migrate(owner)
        owner.commit()
    try:
        yield name
    finally:
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


@needs_db
def test_ingest_search_and_versioning(kb, tmp_path):
    with psycopg.connect(make_conninfo(DSN_ETL, dbname=kb)) as etl:
        first = ingest_directory(etl, SOURCES_DIR)
        assert {r["status"] for r in first} == {"created"} and all(r["chunks"] >= 1 for r in first)
        assert {r["status"] for r in ingest_directory(etl, SOURCES_DIR)} == {"unchanged"}

        changed = write(tmp_path, "niveis.md", url="https://www.voeazul.com.br/br/pt/programa-fidelidade/niveis", body="# Niveis\n\nTexto novo e atualizado da regra de niveis.")
        result = ingest_directory(etl, tmp_path)[0]
        assert (result["status"], result["version"]) == ("new_version", 2) and changed.exists()

    with psycopg.connect(make_conninfo(DSN_RO, dbname=kb)) as ro:
        versions = ro.execute("SELECT version, is_current FROM knowledge.public_sources WHERE url LIKE '%/niveis' ORDER BY version").fetchall()
        assert versions == [(1, False), (2, True)]
        assert ro.execute("SELECT count(*) FROM knowledge.rule_chunks WHERE vector_dims(embedding) = 256").fetchone()[0] == ro.execute(
            "SELECT count(*) FROM knowledge.rule_chunks").fetchone()[0]
        hits = search_rules(ro, "texto atualizado da regra de niveis", k=3)
        assert hits and hits[0]["version"] == 2 and hits[0]["url"].endswith("/niveis") and hits[0]["consulted_at"] == date(2026, 10, 14)
        assert all(h["version"] != 1 or not h["url"].endswith("/niveis") for h in hits)  # versao antiga fora da busca
        assert {"section", "source_url", "source_version", "consulted_at"} <= set(hits[0]["metadata"])
        assert hits[0]["score"] >= hits[-1]["score"]
        assert len(search_rules(ro, "x" * 5000, k=999)) <= 10


@needs_db
def test_knowledge_privileges_and_immutability(kb):
    with psycopg.connect(make_conninfo(DSN_RO, dbname=kb), autocommit=True) as ro:
        for stmt in ("DELETE FROM knowledge.public_sources", "UPDATE knowledge.public_sources SET is_current = false"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                ro.execute(stmt)
    with psycopg.connect(make_conninfo(DSN_ETL, dbname=kb), autocommit=True) as etl:
        for stmt in ("DELETE FROM knowledge.rule_chunks", "TRUNCATE knowledge.rule_chunks", "UPDATE knowledge.public_sources SET title = 'x'"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                etl.execute(stmt)
    with psycopg.connect(make_conninfo(DSN, dbname=kb), autocommit=True) as owner:  # trigger vale ate para o owner
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            owner.execute("UPDATE knowledge.rule_chunks SET content = 'adulterado'")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            owner.execute("UPDATE knowledge.public_sources SET url = 'https://x.example'")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            owner.execute("DELETE FROM knowledge.public_sources")
