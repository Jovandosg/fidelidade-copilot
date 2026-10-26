"""Testes da API somente leitura. Parte estatica roda sem banco; parte viva usa banco temporario + login real do papel somente-leitura."""
import os
import uuid

import pandas as pd
import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo

from scripts.export_openapi import TARGET, render
from src import db
from src.api.main import app
from src.api.security import issue_token
from src.pipeline import ROOT, main
from src.schemas import CustomerFeature, RouteMetric

DSN, DSN_RO = os.environ.get("DATABASE_URL"), os.environ.get("DATABASE_URL_RO")
needs_db = pytest.mark.skipif(not (DSN and DSN_RO), reason="DATABASE_URL/DATABASE_URL_RO nao definidos")
TEST_SECRET = "test-secret-" + "x" * 32

PII = {"name", "email", "cpf", "phone", "birth_date", "nome", "telefone"}


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    app.state.limiter.reset()


def _auth(role: str = "analista") -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_token('tester', role, secret=TEST_SECRET)}"}


# ---------- estaticos (sem banco) ----------
def test_only_the_approval_endpoint_writes():
    ops = {(m.upper(), p) for p, v in app.openapi()["paths"].items() for m in v}
    assert {(m, p) for m, p in ops if m != "GET"} == {("POST", "/nba/{customer_id}/aprovacao")}


def test_openapi_exposes_required_endpoints_and_mirrors_tables():
    spec = app.openapi()
    assert {"/kpis", "/clientes", "/clientes/{customer_id}", "/rotas", "/nba"} <= set(spec["paths"])
    schemas = spec["components"]["schemas"]
    assert set(schemas["CustomerFeature"]["properties"]) == set(CustomerFeature.model_fields)
    assert set(schemas["RouteMetric"]["properties"]) == set(RouteMetric.model_fields)


def test_openapi_has_no_pii_fields():
    props = {p for s in app.openapi()["components"]["schemas"].values() for p in s.get("properties", {})}
    assert not PII & props


def test_committed_openapi_is_up_to_date():
    assert TARGET.read_text(encoding="utf-8").replace("\r\n", "\n") == render()


def test_cors_is_restricted():
    c = TestClient(app)
    ok = c.get("/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    bad = c.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
    pre = c.options("/kpis", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "DELETE"})
    assert pre.status_code == 400


def test_without_database_url_returns_503(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_RO", raising=False)
    assert TestClient(app).get("/kpis", headers=_auth()).status_code == 503


# ---------- vivos ----------
@pytest.fixture(scope="module")
def client():
    name = f"fidelidade_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    main()
    a = ROOT / "data" / "analytics"
    features, routes = pd.read_csv(a / "customer_features.csv"), pd.read_csv(a / "route_metrics.csv")
    with psycopg.connect(make_conninfo(DSN, dbname=name)) as owner:
        db.migrate(owner)
        db.load_analytics(owner, features, routes)
        owner.commit()
    mp = pytest.MonkeyPatch()
    mp.setenv("DATABASE_URL_RO", make_conninfo(DSN_RO, dbname=name))
    try:
        yield TestClient(app, headers=_auth()), features, routes
    finally:
        mp.undo()
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


@needs_db
def test_kpis(client):
    c, features, routes = client
    r = c.get("/kpis").json()
    assert r["synthetic_data"] is True and r["total_customers"] == len(features)
    assert r["avg_hvs"] == pytest.approx(features.hvs.mean(), abs=0.01)
    assert r["high_risk_customers"] == int((features.risk_score >= 40).sum())
    assert r["nba_pending_approval"] == int(features.nba_requires_approval.sum())
    assert sum(p["customers"] for p in r["profiles"]) == len(features)
    assert c.get("/kpis", params={"risk_threshold": 101}).status_code == 422


@needs_db
def test_clientes_pagination_filters_and_sort(client):
    c, features, _ = client
    r = c.get("/clientes", params={"limit": 10, "offset": 5}).json()
    assert r["total"] == len(features) and len(r["items"]) == 10 and r["offset"] == 5
    hvs = [i["hvs"] for i in r["items"]]
    assert hvs == sorted(hvs, reverse=True)
    r = c.get("/clientes", params={"profile": "A", "min_risk": 30, "limit": 200}).json()
    assert r["total"] == int(((features.profile == "A") & (features.risk_score >= 30)).sum())
    assert all(i["profile"] == "A" and i["risk_score"] >= 30 for i in r["items"])
    assert c.get("/clientes", params={"segment": "Estratégico"}).json()["total"] == int((features.segment == "Estratégico").sum())
    assert set(c.get("/clientes").json()["items"][0]) == set(CustomerFeature.model_fields)


@needs_db
def test_clientes_rejects_bad_params_and_injection(client):
    c, features, _ = client
    assert c.get("/clientes", params={"limit": 1000}).status_code == 422
    assert c.get("/clientes", params={"offset": -1}).status_code == 422
    assert c.get("/clientes", params={"profile": "Z"}).status_code == 422
    assert c.get("/clientes", params={"sort": "hvs; DROP TABLE analytics.customer_features"}).status_code == 422
    r = c.get("/clientes", params={"segment": "x' OR '1'='1"})
    assert r.status_code == 200 and r.json()["total"] == 0
    assert c.get("/kpis").json()["total_customers"] == len(features)


@needs_db
def test_cliente_detail_and_404(client):
    c, features, _ = client
    cid = features.customer_id.iloc[0]
    r = c.get(f"/clientes/{cid}")
    assert r.status_code == 200 and r.json()["customer_id"] == cid and r.json()["risk_drivers"]
    assert c.get("/clientes/C999999").status_code == 404
    assert c.get("/clientes/abc").status_code == 422


@needs_db
def test_rotas_and_nba(client):
    c, features, routes = client
    r = c.get("/rotas", params={"limit": 5}).json()
    assert r["total"] == len(routes) and len(r["items"]) == 5
    assert [i["ivr"] for i in r["items"]] == sorted((i["ivr"] for i in r["items"]), reverse=True)
    n = c.get("/nba", params={"requires_approval": True, "limit": 200}).json()
    assert n["total"] == int(features.nba_requires_approval.sum()) and "aprovacao humana" in n["human_approval_notice"]
    assert all(i["nba_requires_approval"] for i in n["items"])
    assert sum(s["customers"] for s in n["summary"]) == len(features)
    assert c.get("/nba", params={"sort": "nope"}).status_code == 422


@needs_db
def test_api_login_cannot_write():
    name_dsn = DSN_RO
    with psycopg.connect(name_dsn) as conn:
        with pytest.raises(psycopg.errors.Error):
            conn.execute("DELETE FROM analytics.customer_features")
