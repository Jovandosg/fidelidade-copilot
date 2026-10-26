"""Ingestao de fontes publicas curadas (knowledge/sources/*.md) em knowledge.public_sources e knowledge.rule_chunks.

Cada arquivo tem um front-matter simples (url, title, publisher, consulted_at, license_note) e o texto da regra em Markdown.
Reingerir conteudo identico nao faz nada; conteudo alterado cria uma nova versao e a anterior deixa de ser corrente.
Nada e coletado da web aqui: o texto e transcrito/curado por uma pessoa a partir da pagina publica citada em `url`.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg.types.json import Jsonb

from ..agent.guardrails import PII_PATTERNS, detect_injection
from .chunking import chunk_markdown
from .embeddings import Embedder, HashingEmbedder, to_pgvector

SOURCES_DIR = Path(__file__).parents[2] / "knowledge" / "sources"
ALLOWED_HOST = "voeazul.com.br"  # somente o dominio publico do programa
MAX_BODY_CHARS = 200_000
REQUIRED = ("url", "title", "publisher", "consulted_at")


class SourceError(ValueError):
    """Arquivo de fonte invalido (nao e ingerido)."""


@dataclass(frozen=True)
class Source:
    url: str
    title: str
    publisher: str
    consulted_at: date
    license_note: str | None
    body: str
    path: Path

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()


def parse_source(path: Path) -> Source:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise SourceError(f"{path.name}: front-matter ausente")
    meta = {}
    for line in match.group(1).splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, sep, value = line.partition(":")
            if not sep:
                raise SourceError(f"{path.name}: linha invalida no front-matter")
            meta[key.strip()] = value.strip().strip("\"'")
    missing = [k for k in REQUIRED if not meta.get(k)]
    if missing:
        raise SourceError(f"{path.name}: campos obrigatorios ausentes: {', '.join(missing)}")
    parsed = urlparse(meta["url"])
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == ALLOWED_HOST or host.endswith("." + ALLOWED_HOST)):
        raise SourceError(f"{path.name}: url fora do dominio publico permitido ({ALLOWED_HOST}) ou sem https")
    try:
        consulted = date.fromisoformat(meta["consulted_at"])
    except ValueError:
        raise SourceError(f"{path.name}: consulted_at deve ser AAAA-MM-DD") from None
    if consulted > date.today():
        raise SourceError(f"{path.name}: consulted_at no futuro")
    body = match.group(2).strip()
    if not body or len(body) > MAX_BODY_CHARS:
        raise SourceError(f"{path.name}: corpo vazio ou grande demais")
    for label, pattern in PII_PATTERNS.items():
        if pattern.search(body):
            raise SourceError(f"{path.name}: possivel PII ({label}) no texto; fontes devem ser regras publicas")
    if detect_injection(body):
        raise SourceError(f"{path.name}: texto com instrucoes dirigidas a modelos (possivel prompt injection); fontes devem ser so regras publicas")
    return Source(meta["url"], meta["title"], meta["publisher"], consulted, meta.get("license_note") or None, body, path)


def ingest_source(conn: psycopg.Connection, source: Source, embedder: Embedder | None = None) -> dict:
    """Ingere uma fonte em uma transacao. Retorna {url, status: created|new_version|unchanged, version, chunks}."""
    embedder = embedder or HashingEmbedder()
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"knowledge:{source.url}",))
        current = conn.execute("SELECT source_id, version, content_hash FROM knowledge.public_sources WHERE url = %s AND is_current", (source.url,)).fetchone()
        if current and current[2] == source.content_hash:
            return {"url": source.url, "status": "unchanged", "version": current[1], "chunks": 0}
        version = 1
        if current:
            conn.execute("UPDATE knowledge.public_sources SET is_current = false WHERE source_id = %s", (current[0],))
            version = conn.execute("SELECT max(version) + 1 FROM knowledge.public_sources WHERE url = %s", (source.url,)).fetchone()[0]
        source_id = conn.execute(
            """INSERT INTO knowledge.public_sources (url, title, publisher, consulted_at, license_note, content_hash, version)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING source_id""",
            (source.url, source.title, source.publisher, source.consulted_at, source.license_note, source.content_hash, version)).fetchone()[0]
        chunks = chunk_markdown(source.body)
        for chunk in chunks:
            metadata = {"section": chunk["section"], "source_url": source.url, "source_version": version,
                        "consulted_at": source.consulted_at.isoformat(), "language": "pt-BR"}
            conn.execute(
                """INSERT INTO knowledge.rule_chunks (source_id, chunk_index, content, metadata, embedding_model, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s::vector)""",
                (source_id, chunk["chunk_index"], chunk["content"], Jsonb(metadata), embedder.model_name, to_pgvector(embedder.embed(chunk["content"]))))
    return {"url": source.url, "status": "created" if version == 1 else "new_version", "version": version, "chunks": len(chunks)}


def ingest_directory(conn: psycopg.Connection, directory: Path = SOURCES_DIR, embedder: Embedder | None = None) -> list[dict]:
    files = sorted(p for p in directory.glob("*.md") if not p.name.startswith("_"))
    return [ingest_source(conn, parse_source(p), embedder) for p in files]


def main(argv: list[str] | None = None) -> None:
    from ..db import get_dsn

    parser = argparse.ArgumentParser(description="Ingere fontes publicas curadas na base de conhecimento (papel etl).")
    parser.add_argument("--dir", type=Path, default=SOURCES_DIR)
    args = parser.parse_args(argv)
    with psycopg.connect(get_dsn("DATABASE_URL_ETL")) as conn:
        for result in ingest_directory(conn, args.dir):
            print(f"{result['status']:<12} v{result['version']} chunks={result['chunks']} {result['url']}")


if __name__ == "__main__":
    main()
