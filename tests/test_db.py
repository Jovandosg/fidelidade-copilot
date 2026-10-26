"""Testes contra um PostgreSQL real (pulados sem DATABASE_URL). Usam um banco temporario descartavel."""
import os
import uuid

import pandas as pd
import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from src import db
from src.contracts import load_contract
from src.pipeline import ROOT, main
from src.schemas import MODELS

DSN = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="DATABASE_URL nao definido")


@pytest.fixture(scope="module")
def conn():
    name = f"fidelidade_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    c = psycopg.connect(make_conninfo(DSN, dbname=name))
    try:
        yield c
    finally:
        c.close()
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


@pytest.fixture(scope="module")
def frames():
    main()
    a = ROOT / "data" / "analytics"
    return pd.read_csv(a / "customer_features.csv"), pd.read_csv(a / "route_metrics.csv")


def test_migrations_are_idempotent_and_checksummed(conn):
    all_files = sorted(p.name for p in db.MIGRATIONS_DIR.glob("*.sql"))
    assert db.migrate(conn) == all_files
    assert db.migrate(conn) == []
    conn.execute("UPDATE public.schema_migrations SET checksum = 'x' WHERE version LIKE '001%'")
    conn.commit()
    with pytest.raises(RuntimeError):
        db.migrate(conn)
    conn.rollback()
    conn.execute("DELETE FROM public.schema_migrations WHERE version LIKE '001%'")  # restaura estado para os proximos testes
    conn.commit()
    conn.execute("DROP SCHEMA analytics, raw, treated, ops CASCADE")
    conn.commit()
    conn.execute("DELETE FROM public.schema_migrations")
    conn.commit()
    assert db.migrate(conn) == all_files


def test_ddl_migrations_can_be_reapplied_without_error(conn):
    """003-006 usam IF NOT EXISTS/GRANT idempotentes: reexecutar o SQL nao pode falhar nem duplicar objetos."""
    for name in ("003_layers_and_roles.sql", "004_raw_treated_tables.sql", "005_ops_tables.sql", "006_grants.sql"):
        conn.execute((db.MIGRATIONS_DIR / name).read_text(encoding="utf-8"))
    conn.commit()


def test_live_tables_match_contract_and_pydantic(conn):
    contract = load_contract()
    for (schema, table), entity in db.LAYER_TABLES.items():
        rows = conn.execute("""SELECT column_name, data_type, is_nullable FROM information_schema.columns
                               WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position""", (schema, table)).fetchall()
        spec = contract["entities"][entity]["columns"]
        assert [r[0] for r in rows] == list(spec), f"{schema}.{table}"
        for name, data_type, nullable in rows:
            assert data_type == {"text": "text", "integer": "integer", "numeric": "numeric", "boolean": "boolean", "date": "date"}[db.PG_TYPES[spec[name]["type"]]]
            assert (nullable == "YES") == spec[name]["nullable"]
        if schema == "analytics":
            assert list(MODELS[entity].model_fields) == list(spec)


def test_load_layers_fills_raw_treated_and_analytics_idempotently(conn, frames):
    first = db.load_layers(conn)
    assert first == db.load_layers(conn)
    assert set(first) == {f"{s}.{t}" for s, t in db.LAYER_TABLES}
    assert first["raw.transactions"] == first["treated.transactions"] > 0
    assert conn.execute("SELECT count(*) FROM raw.transactions t LEFT JOIN raw.customers c USING (customer_id) WHERE c.customer_id IS NULL").fetchone()[0] == 0
    conn.commit()


def test_upsert_is_idempotent_updates_and_removes_stale(conn, frames):
    features, routes = frames
    assert db.load_analytics(conn, features, routes) == {"customer_features": len(features), "route_metrics": len(routes)}
    assert db.load_analytics(conn, features, routes) == {"customer_features": len(features), "route_metrics": len(routes)}
    assert conn.execute("SELECT count(*) FROM analytics.customer_features").fetchone()[0] == len(features)

    changed = features.copy()
    changed.loc[0, "hvs"] = 1.23
    changed = changed.iloc[:-5]
    db.load_analytics(conn, changed, routes)
    conn.commit()
    assert float(conn.execute("SELECT hvs FROM analytics.customer_features WHERE customer_id = %s", (features.customer_id[0],)).fetchone()[0]) == pytest.approx(1.23)

    assert conn.execute("SELECT count(*) FROM analytics.customer_features").fetchone()[0] == len(features) - 5
    db.load_analytics(conn, features, routes)


def test_rows_round_trip_through_pydantic(conn, frames):
    features, routes = frames
    cur = conn.cursor(row_factory=psycopg.rows.dict_row)
    row = cur.execute("SELECT * FROM analytics.customer_features ORDER BY customer_id LIMIT 1").fetchone()
    assert MODELS["customer_features"].model_validate(row).customer_id == features.customer_id.min()
    row = cur.execute("SELECT * FROM analytics.route_metrics ORDER BY route LIMIT 1").fetchone()
    MODELS["route_metrics"].model_validate(row)


def test_invalid_data_is_rejected_before_and_inside_database(conn, frames):
    features, routes = frames
    bad = features.copy()
    bad.loc[0, "hvs"] = 150.0
    with pytest.raises(Exception):
        db.load_analytics(conn, bad, routes)  # pandera barra antes do SQL
    conn.rollback()
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("UPDATE analytics.customer_features SET hvs = 150 WHERE customer_id = %s", (features.customer_id[0],))
    conn.rollback()


def test_readonly_role_can_select_but_not_write(conn):
    conn.execute("SET ROLE fidelidade_ro")
    try:
        assert conn.execute("SELECT count(*) FROM analytics.customer_features").fetchone()[0] > 0
        for stmt in ("DELETE FROM analytics.customer_features", "UPDATE analytics.route_metrics SET ivr = 0",
                     "INSERT INTO analytics.route_metrics SELECT * FROM analytics.route_metrics", "DROP TABLE analytics.route_metrics"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(stmt)
            conn.rollback()
            conn.execute("SET ROLE fidelidade_ro")
    finally:
        conn.rollback()
        conn.execute("RESET ROLE")
        conn.commit()


OPS_TABLES = ("pipeline_runs", "data_quality_results", "model_registry", "drift_metrics", "audit_log")
AUDIT_ROW = ("INSERT INTO ops.audit_log (actor, actor_role, action, entity, entity_id, before, after) "
              "VALUES ('u1', 'gestor', 'approve_nba', 'nba', 'C000001', '{}', '{\"ok\": true}')")


def _as(conn, role, stmt, params=None):
    conn.execute(f"SET ROLE {role}")
    try:
        return conn.execute(stmt, params).fetchall() if stmt.lstrip().upper().startswith("SELECT") else conn.execute(stmt, params)
    finally:
        conn.rollback()
        conn.execute("RESET ROLE")
        conn.commit()


def test_ops_tables_exist(conn):
    found = {r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'ops'").fetchall()}
    assert set(OPS_TABLES) <= found


def test_audit_log_is_append_only_even_for_owner(conn):
    conn.execute(AUDIT_ROW)
    conn.commit()
    for stmt in ("UPDATE ops.audit_log SET actor = 'x'", "DELETE FROM ops.audit_log", "TRUNCATE ops.audit_log"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(stmt)
        conn.rollback()
    assert conn.execute("SELECT count(*) FROM ops.audit_log").fetchone()[0] >= 1


def test_audit_role_can_only_insert_and_select_audit_log(conn):
    assert _as(conn, "fidelidade_api_audit", "SELECT count(*) FROM ops.audit_log")[0][0] >= 1
    conn.execute("SET ROLE fidelidade_api_audit")
    conn.execute(AUDIT_ROW)
    conn.rollback()
    conn.execute("RESET ROLE")
    for stmt in ("UPDATE ops.audit_log SET actor = 'x'", "DELETE FROM ops.audit_log", "INSERT INTO analytics.route_metrics SELECT * FROM analytics.route_metrics",
                 "SELECT 1 FROM ops.model_registry", "SELECT 1 FROM raw.customers"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _as(conn, "fidelidade_api_audit", stmt)


def test_readonly_role_reads_ops_but_not_audit_log_nor_raw(conn):
    for ok in ("SELECT count(*) FROM ops.pipeline_runs", "SELECT count(*) FROM ops.drift_metrics"):
        _as(conn, "fidelidade_ro", ok)
    for stmt in ("SELECT 1 FROM ops.audit_log", "SELECT 1 FROM raw.customers", "SELECT 1 FROM treated.transactions",
                 "INSERT INTO ops.pipeline_runs (run_id, started_at, status, code_version, seed, contract_version) "
                 "VALUES (gen_random_uuid(), now(), 'running', 'x', 1, '1.1.0')"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _as(conn, "fidelidade_ro", stmt)


def test_etl_role_writes_layers_but_not_audit_log(conn):
    _as(conn, "fidelidade_etl", "UPDATE analytics.route_metrics SET ivr = ivr")
    _as(conn, "fidelidade_etl", "SELECT count(*) FROM raw.customers")
    for stmt in (AUDIT_ROW, "SELECT 1 FROM ops.audit_log", "UPDATE ops.audit_log SET actor = 'x'"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _as(conn, "fidelidade_etl", stmt)


def test_ops_constraints_reject_bad_values(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO ops.pipeline_runs (run_id, started_at, status, code_version, seed, contract_version) "
                     "VALUES (gen_random_uuid(), now(), 'bogus', 'x', 1, '1.1.0')")
    conn.rollback()
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(AUDIT_ROW.replace("'gestor'", "'root'"))
    conn.rollback()


def test_record_run_is_idempotent_and_runs_as_etl(conn):
    from src.runs import read_run_report

    main()
    rep = read_run_report()
    conn.execute("SET ROLE fidelidade_etl")
    try:
        n = db.record_run(conn, rep)
        db.record_run(conn, rep)
        conn.commit()
    finally:
        conn.rollback()
        conn.execute("RESET ROLE")
        conn.commit()
    assert n == len(rep["rules"]) > 10
    row = conn.execute("SELECT status, seed, rows_by_entity->>'customers_raw' FROM ops.pipeline_runs WHERE run_id = %s", (rep["run_id"],)).fetchone()
    assert row == ("passed", rep["seed"], "1200")
    assert conn.execute("SELECT count(*) FROM ops.data_quality_results WHERE run_id = %s", (rep["run_id"],)).fetchone()[0] == n
    failed = {**rep, "run_id": str(uuid.uuid4()), "status": "failed", "error": "boom", "rules": [{"entity": "route_metrics", "rule": "ivr:x", "passed": False, "failed_rows": 3}]}
    db.record_run(conn, failed)
    conn.commit()
    assert conn.execute("SELECT status, error FROM ops.pipeline_runs WHERE run_id = %s", (failed["run_id"],)).fetchone() == ("failed", "boom")


def test_record_run_persists_models_and_drift_idempotently(conn):
    from src.drift import compute_drift, snapshot
    from src.runs import read_run_report

    main()
    rep = read_run_report()
    feats = pd.read_csv(ROOT / "data" / "analytics" / "customer_features.csv")
    rep["drift"] = compute_drift(feats.assign(recency_days=feats["recency_days"] + 400), snapshot(feats))
    db.record_run(conn, rep)
    conn.commit()
    conn.execute("SET ROLE fidelidade_etl")
    try:
        db.record_run(conn, rep)
        conn.commit()
    finally:
        conn.rollback()
        conn.execute("RESET ROLE")
        conn.commit()
    names = {r[0] for r in conn.execute("SELECT model_name FROM ops.model_registry WHERE data_hash = %s", (rep["models"][0]["data_hash"],)).fetchall()}
    assert names == {"hvs", "risk", "nba"}
    assert conn.execute("SELECT count(*) FROM ops.model_registry WHERE data_hash = %s", (rep["models"][0]["data_hash"],)).fetchone()[0] == 3
    assert "Metricas calculadas sobre dados sinteticos" in conn.execute("SELECT synthetic_notice FROM ops.model_registry LIMIT 1").fetchone()[0]
    alerts = {r[0] for r in conn.execute("SELECT feature FROM ops.drift_metrics WHERE run_id = %s AND alert", (rep["run_id"],)).fetchall()}
    assert "recency_days" in alerts
    assert conn.execute("SELECT count(*) FROM ops.drift_metrics WHERE run_id = %s", (rep["run_id"],)).fetchone()[0] == len(rep["drift"])
