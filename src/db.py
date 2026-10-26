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
from psycopg.types.json import Jsonb

from .contracts import build_schema, load_contract
from .runs import read_run_report

ROOT = Path(__file__).parents[1]
MIGRATIONS_DIR = ROOT / "db" / "migrations"
SCHEMA = "analytics"
ENTITIES = ("customer_features", "route_metrics")  # entidades do contrato persistidas em analytics
# (schema, tabela) -> entidade do contrato que a define; customers antes de transactions
LAYER_TABLES = {
    ("raw", "customers"): "customers_raw", ("raw", "transactions"): "transactions_raw",
    ("treated", "customers"): "customers_raw", ("treated", "transactions"): "transactions_raw",
    ("analytics", "customer_features"): "customer_features", ("analytics", "route_metrics"): "route_metrics",
}
PG_TYPES = {"string": "text", "integer": "integer", "decimal": "numeric", "boolean": "boolean", "date": "date"}


def get_dsn(var: str = "DATABASE_URL") -> str:
    dsn = os.environ.get(var)
    if not dsn:
        raise RuntimeError(f"{var} nao definido (veja .env.example)")
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


def load_table(conn: psycopg.Connection, entity: str, df: pd.DataFrame, contract: dict | None = None,
               schema: str = SCHEMA, table_name: str | None = None) -> int:
    """Upsert por chave primaria e remocao de linhas ausentes (a tabela espelha o snapshot do pipeline)."""
    contract = contract or load_contract()
    ent = contract["entities"][entity]
    columns = list(ent["columns"])
    pk = ent["primary_key"]
    build_schema(entity, contract).validate(df[columns], lazy=True)
    table = sql.Identifier(schema, table_name or entity)
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


def load_layers(conn: psycopg.Connection, data_dir: Path = ROOT / "data") -> dict[str, int]:
    """Carrega raw, treated e analytics a partir dos CSVs do pipeline (customers antes de transactions)."""
    contract = load_contract()
    counts = {}
    for (schema, table), entity in LAYER_TABLES.items():
        layer_dir = data_dir / schema
        df = pd.read_csv(layer_dir / f"{table}.csv") if schema != "analytics" else pd.read_csv(layer_dir / f"{entity}.csv")
        counts[f"{schema}.{table}"] = load_table(conn, entity, df, contract, schema, table)
    return counts


def record_run(conn: psycopg.Connection, report: dict) -> int:
    """Persiste a execucao e o resultado por regra em ops.* (idempotente por run_id); devolve o numero de regras."""
    with conn.transaction():
        conn.execute(
            """INSERT INTO ops.pipeline_runs (run_id, started_at, finished_at, duration_ms, status, code_version, seed, contract_version, rows_by_entity, error)
               VALUES (%(run_id)s, %(started_at)s, %(finished_at)s, %(duration_ms)s, %(status)s, %(code_version)s, %(seed)s, %(contract_version)s, %(rows)s, %(error)s)
               ON CONFLICT (run_id) DO UPDATE SET finished_at = EXCLUDED.finished_at, duration_ms = EXCLUDED.duration_ms,
                   status = EXCLUDED.status, rows_by_entity = EXCLUDED.rows_by_entity, error = EXCLUDED.error""",
            {**report, "rows": Jsonb(report["rows_by_entity"]), "error": report.get("error")})
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO ops.data_quality_results (run_id, entity, rule, passed, failed_rows)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (run_id, entity, rule) DO UPDATE SET passed = EXCLUDED.passed, failed_rows = EXCLUDED.failed_rows""",
                [(report["run_id"], r["entity"], r["rule"], r["passed"], r["failed_rows"]) for r in report.get("rules", [])])
    return len(report.get("rules", []))


def main(argv: list[str] | None = None) -> None:
    cmd = (argv or sys.argv[1:] or ["all"])[0]
    if cmd in ("migrate", "all"):
        with psycopg.connect(get_dsn()) as conn:  # DDL exige o dono do schema
            print("migracoes aplicadas:", migrate(conn) or "nenhuma pendente")
    if cmd in ("load", "all"):
        dsn = os.environ.get("DATABASE_URL_ETL") or get_dsn()  # carga com o papel etl quando configurado
        with psycopg.connect(dsn) as conn:
            run = read_run_report()
            if run:
                print("execucao do pipeline registrada em ops:", run["run_id"], run["status"], f"({record_run(conn, run)} regras)")
                if run["status"] != "passed":
                    raise SystemExit("ultima execucao do pipeline falhou; dados nao carregados (veja ops.pipeline_runs.error)")
            else:
                print("aviso: data/analytics/run_report.json ausente; execucao nao registrada em ops (rode python -m src.pipeline)")
            print("linhas carregadas:", load_layers(conn))


if __name__ == "__main__":
    main()
