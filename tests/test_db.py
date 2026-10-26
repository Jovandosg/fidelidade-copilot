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
    assert db.migrate(conn) == ["001_analytics_schema.sql", "002_readonly_role.sql"]
    assert db.migrate(conn) == []
    conn.execute("UPDATE public.schema_migrations SET checksum = 'x' WHERE version LIKE '001%'")
    conn.commit()
    with pytest.raises(RuntimeError):
        db.migrate(conn)
    conn.rollback()
    conn.execute("DELETE FROM public.schema_migrations WHERE version LIKE '001%'")  # restaura estado para os proximos testes
    conn.commit()
    conn.execute("DROP SCHEMA analytics CASCADE")
    conn.commit()
    conn.execute("DELETE FROM public.schema_migrations")
    conn.commit()
    assert len(db.migrate(conn)) == 2


def test_live_tables_match_contract_and_pydantic(conn):
    contract = load_contract()
    for entity in db.ENTITIES:
        rows = conn.execute("""SELECT column_name, data_type, is_nullable FROM information_schema.columns
                               WHERE table_schema = 'analytics' AND table_name = %s ORDER BY ordinal_position""", (entity,)).fetchall()
        spec = contract["entities"][entity]["columns"]
        assert [r[0] for r in rows] == list(spec)
        for name, data_type, nullable in rows:
            assert data_type == {"text": "text", "integer": "integer", "numeric": "numeric", "boolean": "boolean", "date": "date"}[db.PG_TYPES[spec[name]["type"]]]
            assert (nullable == "YES") == spec[name]["nullable"]
        assert list(MODELS[entity].model_fields) == list(spec)


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
