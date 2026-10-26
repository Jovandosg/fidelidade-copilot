"""Migracoes versionadas e carga idempotente (upsert) das tabelas analytics.* no PostgreSQL.

Uso:  python -m src.db [migrate|load|all]   (DATABASE_URL no ambiente; padrao: all)
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg
from psycopg import sql

from .contracts import build_schema, load_contract

ROOT = Path(__file__).parents[1]
MIGRATIONS_DIR = ROOT / "db" / "migrations"
SCHEMA = "analytics"
ENTITIES = ("customer_features", "route_metrics")  # entidades do contrato persistidas no Postgres
PG_TYPES = {"string": "text", "integer": "integer", "decimal": "numeric", "boolean": "boolean", "date": "date"}


def get_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL nao definido (veja .env.example)")
    return dsn


def migrate(conn: psycopg.Connection) -> list[str]:
    """Aplica migracoes pendentes em ordem; falha se uma migracao ja aplicada foi alterada."""
    with conn.transaction():
        conn.execute("""CREATE TABLE IF NOT EXISTS public.schema_migrations (
            version text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())""")
        conn.execute("SELECT pg_advisory_xact_lock(748201)")  # evita migracoes concorrentes
        applied = dict(conn.execute("SELECT version, checksum FROM public.schema_migrations").fetchall())
        done = []
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            text = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if path.name in applied:
                if applied[path.name] != checksum:
                    raise RuntimeError(f"migracao {path.name} foi alterada depois de aplicada; crie uma nova")
                continue
            conn.execute(text)
            conn.execute("INSERT INTO public.schema_migrations (version, checksum) VALUES (%s, %s)", (path.name, checksum))
            done.append(path.name)
    return done


def _rows(df: pd.DataFrame, columns: list[str]) -> list[list]:
    return df[columns].astype(object).where(df[columns].notna(), None).values.tolist()


def load_table(conn: psycopg.Connection, entity: str, df: pd.DataFrame, contract: dict | None = None) -> int:
    """Upsert por chave primaria e remocao de linhas ausentes (a tabela espelha o snapshot do pipeline)."""
    contract = contract or load_contract()
    ent = contract["entities"][entity]
    columns = list(ent["columns"])
    pk = ent["primary_key"]
    build_schema(entity, contract).validate(df[columns], lazy=True)
    table = sql.Identifier(SCHEMA, entity)
    updates = [sql.SQL("{c} = EXCLUDED.{c}").format(c=sql.Identifier(c)) for c in columns if c != pk]
    upsert = sql.SQL("INSERT INTO {t} ({cols}) VALUES ({ph}) ON CONFLICT ({pk}) DO UPDATE SET {upd}").format(
        t=table, cols=sql.SQL(", ").join(map(sql.Identifier, columns)), ph=sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        pk=sql.Identifier(pk), upd=sql.SQL(", ").join(updates))
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(upsert, _rows(df, columns))
            cur.execute(sql.SQL("DELETE FROM {t} WHERE {pk} <> ALL(%s)").format(t=table, pk=sql.Identifier(pk)), (df[pk].tolist(),))
    return len(df)


def load_analytics(conn: psycopg.Connection, features: pd.DataFrame, routes: pd.DataFrame) -> dict[str, int]:
    contract = load_contract()
    return {"customer_features": load_table(conn, "customer_features", features, contract),
            "route_metrics": load_table(conn, "route_metrics", routes, contract)}


def main(argv: list[str] | None = None) -> None:
    cmd = (argv or sys.argv[1:] or ["all"])[0]
    with psycopg.connect(get_dsn()) as conn:
        if cmd in ("migrate", "all"):
            print("migracoes aplicadas:", migrate(conn) or "nenhuma pendente")
        if cmd in ("load", "all"):
            analytics = ROOT / "data" / "analytics"
            counts = load_analytics(conn, pd.read_csv(analytics / "customer_features.csv"), pd.read_csv(analytics / "route_metrics.csv"))
            print("linhas carregadas:", counts)


if __name__ == "__main__":
    main()
