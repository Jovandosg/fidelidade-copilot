"""Busca semantica nas regras publicas correntes. Cada resultado carrega a fonte (URL, data de consulta, versao) para citacao obrigatoria."""
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from .embeddings import Embedder, HashingEmbedder, to_pgvector

SQL = """
SELECT c.chunk_id, c.content, c.metadata, s.source_id, s.url, s.title, s.consulted_at, s.version,
       (1 - (c.embedding <=> %(v)s::vector))::float8 AS score
FROM knowledge.rule_chunks c JOIN knowledge.public_sources s USING (source_id)
WHERE s.is_current AND c.embedding_model = %(m)s
ORDER BY c.embedding <=> %(v)s::vector, c.chunk_id
LIMIT %(k)s
"""


def search_rules(conn: psycopg.Connection, query: str, k: int = 3, embedder: Embedder | None = None) -> list[dict]:
    embedder = embedder or HashingEmbedder()
    k = max(1, min(k, 10))
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(SQL, {"v": to_pgvector(embedder.embed(query[:1000])), "m": embedder.model_name, "k": k}).fetchall()
