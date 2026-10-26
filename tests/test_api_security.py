"""Seguranca da API: JWT/RBAC, rate limit, headers, logs estruturados, ops/auditoria e aprovacao (com banco temporario)."""
import json
import logging
import os
import time
import uuid

import jwt
import pandas as pd
import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo

from src import db
from src.api.main import app, create_app
from src.api.security import ALGORITHM, ISSUER, RateLimiter, issue_token
from src.drift import compute_drift, snapshot
from src.pipeline import ROOT, main
from src.runs import read_run_report

DSN, DSN_RO, DSN_AUDIT = (os.environ.get(v) for v in ("DATABASE_URL", "DATABASE_URL_RO", "DATABASE_URL_AUDIT"))
needs_db = pytest.mark.skipif(not (DSN and DSN_RO and DSN_AUDIT), reason="DATABASE_URL, _RO e _AUDIT nao definidos")
SECRET = "unit-test-secret-" + "y" * 32


def tok(role="analista", sub="tester", **kw):
    return {"Authorization": f"Bearer {issue_token(sub, role, secret=SECRET, **kw)}"}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    app.state.limiter.reset()


def forged(claims: dict, key=SECRET, alg=ALGORITHM) -> dict:
    return {"Authorization": f"Bearer {jwt.encode(claims, key, algorithm=alg)}"}


def base_claims(**over) -> dict:
    now = int(time.time())
    return {"iss": ISSUER, "sub": "tester", "role": "gestor", "iat": now, "exp": now + 600, **over}


# ---------- JWT (sem banco: a autenticacao ocorre antes de qualquer consulta) ----------
PROTECTED = ["/kpis", "/clientes", "/clientes/C000001", "/rotas", "/nba", "/ops/runs", "/ops/quality", "/ops/models", "/ops/drift", "/audit", "/nba/aprovacoes"]


@pytest.mark.parametrize("path", PROTECTED)
def test_endpoints_require_a_token(path):
    r = TestClient(app).get(path)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


def test_health_is_public():
    assert TestClient(app).get("/health").status_code == 200


@pytest.mark.parametrize("headers", [
    {"Authorization": "Bearer lixo"},
    {"Authorization": "Basic abc"},
    forged(base_claims(), key="outro-segredo-" + "z" * 32),
    forged(base_claims(exp=int(time.time()) - 10)),
    forged(base_claims(iss="outro")),
    forged(base_claims(role="root")),
    forged(base_claims(sub="Maria Silva <maria@x.com>")),
    forged({k: v for k, v in base_claims().items() if k != "exp"}),
    forged(base_claims(exp=int(time.time()) + 10 * 24 * 3600)),
])
def test_invalid_tokens_are_rejected(headers):
    assert TestClient(app).get("/kpis", headers=headers).status_code == 401


def test_alg_none_is_rejected():
    header = jwt.utils.base64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode()
    body = jwt.utils.base64url_encode(json.dumps(base_claims()).encode()).decode()
    assert TestClient(app).get("/kpis", headers={"Authorization": f"Bearer {header}.{body}."}).status_code == 401


def test_without_configured_secret_auth_fails_closed(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "curto")
    assert TestClient(app).get("/kpis", headers=tok()).status_code == 503


def test_issue_token_validates_inputs():
    for bad in ({"sub": "Maria Silva", "role": "gestor"}, {"sub": "ok", "role": "admin"}, {"sub": "ok", "role": "gestor", "ttl_seconds": 10**7}):
        with pytest.raises(ValueError):
            issue_token(secret=SECRET, **bad)
    with pytest.raises(ValueError):
        issue_token("ok", "gestor", secret="curto")


@pytest.mark.parametrize("role,method,path,ok", [
    ("analista", "get", "/audit", False), ("gestor", "get", "/audit", False), ("auditor", "get", "/audit", True),
    ("analista", "get", "/nba/aprovacoes", False), ("gestor", "get", "/nba/aprovacoes", True), ("auditor", "get", "/nba/aprovacoes", True),
    ("analista", "post", "/nba/C000001/aprovacao", False), ("auditor", "post", "/nba/C000001/aprovacao", False),
])
def test_rbac_matrix_for_restricted_endpoints(role, method, path, ok):
    # sem banco configurado: permitido => 503 (passou da autorizacao); proibido => 403 antes de tocar no banco
    env = {k: os.environ.pop(k) for k in ("DATABASE_URL_AUDIT",) if k in os.environ}
    try:
        kwargs = {"json": {"decision": "approve", "reason": "justificativa valida"}} if method == "post" else {}
        r = getattr(TestClient(app), method)(path, headers=tok(role), **kwargs)
    finally:
        os.environ.update(env)
    assert (r.status_code == 503) if ok else (r.status_code == 403)


# ---------- rate limit ----------
def test_limiter_sliding_window():
    lim = RateLimiter(read_per_min=2, write_per_min=1)
    assert lim.check("a", "read", 0) == 0 and lim.check("a", "read", 1) == 0
    assert lim.check("a", "read", 2) > 0
    assert lim.check("b", "read", 2) == 0 and lim.check("a", "write", 2) == 0 and lim.check("a", "write", 3) > 0
    assert lim.check("a", "read", 61) == 0


def test_api_returns_429_with_retry_after(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    monkeypatch.delenv("DATABASE_URL_RO", raising=False)
    c = TestClient(create_app())
    codes = [c.get("/kpis", headers=tok()).status_code for _ in range(5)]
    assert codes[:3] == [503] * 3 and codes[3:] == [429, 429]
    r = c.get("/kpis", headers=tok())
    assert int(r.headers["retry-after"]) >= 1
    assert c.get("/health").status_code == 200  # health fora do limite


# ---------- headers e logs ----------
def test_security_headers_and_request_id():
    r = TestClient(app).get("/kpis")
    h = r.headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY" and h["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in h["content-security-policy"] and h["cache-control"] == "no-store" and "strict-transport-security" in h
    assert len(h["x-request-id"]) == 32
    assert TestClient(app).get("/health", headers={"X-Request-ID": "abc-123"}).headers["x-request-id"] == "abc-123"
    assert TestClient(app).get("/health", headers={"X-Request-ID": "x\ny"}).headers["x-request-id"] != "x\ny"


def test_structured_log_has_no_token_or_query(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_RO", raising=False)
    records: list[logging.LogRecord] = []

    class Grab(logging.Handler):
        def emit(self, record):
            records.append(record)

    grab = Grab()
    logging.getLogger("ancora.api").addHandler(grab)
    try:
        headers = tok("gestor", "maria.gestora")
        TestClient(app).get("/clientes/C000001?segment=segredo", headers=headers)
    finally:
        logging.getLogger("ancora.api").removeHandler(grab)
    entry = json.loads(records[0].getMessage())
    assert entry["event"] == "http_request" and entry["status"] in (404, 503) and entry["method"] == "GET"
    assert entry["path"] == "/clientes/{customer_id}" and entry["sub"] == "maria.gestora" and entry["role"] == "gestor"
    assert {"request_id", "duration_ms", "ts"} <= set(entry)
    text = json.dumps(entry)
    assert "segredo" not in text and headers["Authorization"].split()[1] not in text


# ---------- com banco: ops, auditoria e aprovacao ----------
@pytest.fixture(scope="module")
def live():
    name = f"fidelidade_sec_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    main()
    a = ROOT / "data" / "analytics"
    features, routes = pd.read_csv(a / "customer_features.csv"), pd.read_csv(a / "route_metrics.csv")
    rep = read_run_report()
    rep["drift"] = compute_drift(features.assign(recency_days=features["recency_days"] + 400), snapshot(features))
    with psycopg.connect(make_conninfo(DSN, dbname=name)) as owner:
        db.migrate(owner)
        db.load_analytics(owner, features, routes)
        db.record_run(owner, rep)
        owner.commit()
    mp = pytest.MonkeyPatch()
    mp.setenv("DATABASE_URL_RO", make_conninfo(DSN_RO, dbname=name))
    mp.setenv("DATABASE_URL_AUDIT", make_conninfo(DSN_AUDIT, dbname=name))
    mp.setenv("JWT_SECRET", SECRET)
    try:
        yield TestClient(app), features, rep, name
    finally:
        mp.undo()
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


@needs_db
def test_ops_endpoints_serve_health_data(live):
    c, _, rep, _ = live
    runs = c.get("/ops/runs", headers=tok()).json()
    assert runs[0]["run_id"] == rep["run_id"] and runs[0]["status"] == "passed" and runs[0]["rows_by_entity"]["customers_raw"] == 1200
    q = c.get("/ops/quality", headers=tok()).json()
    assert q["run_id"] == rep["run_id"] and q["total_rules"] == len(rep["rules"]) and q["failed_rules"] == 0
    models = {m["model_name"]: m for m in c.get("/ops/models", headers=tok()).json()}
    assert set(models) == {"hvs", "risk", "nba"} and "sinteticos" in models["risk"]["synthetic_notice"]
    d = c.get("/ops/drift", headers=tok()).json()
    assert d["alerts"] >= 1 and d["items"][0]["feature"] in {"recency_days", "profile"} and d["items"][0]["alert"]
    assert c.get("/ops/quality", params={"run_id": "nao-uuid"}, headers=tok()).status_code == 422
    assert c.get("/ops/quality", params={"run_id": str(uuid.uuid4())}, headers=tok()).json()["total_rules"] == 0


@needs_db
def test_approval_writes_immutable_audit_trail(live):
    c, features, _, name = live
    cid = features.loc[features.nba_requires_approval, "customer_id"].iloc[0]
    body = {"decision": "approve", "reason": "Dentro da politica de retencao"}
    assert c.post(f"/nba/{cid}/aprovacao", json=body, headers=tok("analista")).status_code == 403
    r = c.post(f"/nba/{cid}/aprovacao", json=body, headers={**tok("gestor", "maria.gestora"), "X-Request-ID": "req-aprov-1"})
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["before"]["approval_status"] == "pending" and out["after"]["approval_status"] == "approved"
    assert out["after"]["reason"] == body["reason"] and out["before"]["nba_action"] == out["after"]["nba_action"]
    entry = c.get("/audit", params={"entity_id": cid}, headers=tok("auditor")).json()["items"][0]
    assert (entry["actor"], entry["actor_role"], entry["action"], entry["entity_id"], entry["request_id"]) == ("maria.gestora", "gestor", "nba.approve", cid, "req-aprov-1")
    assert entry["before"] == out["before"] and entry["after"] == out["after"] and entry["occurred_at"]
    assert c.post(f"/nba/{cid}/aprovacao", json={"decision": "reject", "reason": "tentando mudar"}, headers=tok("gestor")).status_code == 409
    status = {s["customer_id"]: s for s in c.get("/nba/aprovacoes", headers=tok("auditor")).json()}
    assert status[cid]["decision"] == "approve" and status[cid]["actor"] == "maria.gestora"
    with psycopg.connect(make_conninfo(DSN, dbname=name)) as owner:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            owner.execute("UPDATE ops.audit_log SET actor = 'x'")


@needs_db
def test_approval_validation_and_unknown_customers(live):
    c, features, _, _ = live
    no_need = features.loc[~features.nba_requires_approval, "customer_id"].iloc[0]
    ok = {"decision": "reject", "reason": "motivo suficiente"}
    assert c.post(f"/nba/{no_need}/aprovacao", json=ok, headers=tok("gestor")).status_code == 409
    assert c.post("/nba/C999999/aprovacao", json=ok, headers=tok("gestor")).status_code == 404
    assert c.post("/nba/abc/aprovacao", json=ok, headers=tok("gestor")).status_code == 422
    need = features.loc[features.nba_requires_approval, "customer_id"].iloc[1]
    for bad in ({"decision": "maybe", "reason": "motivo suficiente"}, {"decision": "approve", "reason": "x"}, {"decision": "approve", "reason": "y" * 501}, {}):
        assert c.post(f"/nba/{need}/aprovacao", json=bad, headers=tok("gestor")).status_code == 422
    rows = c.get("/audit", params={"entity_id": need}, headers=tok("auditor")).json()
    assert rows["total"] == 0


@needs_db
def test_audit_requires_auditor_and_validates_filters(live):
    c, _, _, _ = live
    assert c.get("/audit", headers=tok("gestor")).status_code == 403
    assert c.get("/audit", params={"entity_id": "x' OR '1'='1"}, headers=tok("auditor")).status_code == 422
    assert c.get("/audit", params={"limit": 1000}, headers=tok("auditor")).status_code == 422
    assert c.get("/audit", headers=tok("auditor")).json()["total"] >= 0


@needs_db
def test_hostile_inputs_never_cause_500_or_leak_details(live):
    c, features, _, _ = live
    need = features.loc[features.nba_requires_approval, "customer_id"].iloc[2]
    hostile = [
        c.post(f"/nba/{need}/aprovacao", content=b"{not json", headers={**tok("gestor"), "Content-Type": "application/json"}),
        c.post(f"/nba/{need}/aprovacao", json={"decision": "approve", "reason": "x" * 2_000_000}, headers=tok("gestor")),
        c.post(f"/nba/{need}/aprovacao", json={"decision": ["approve"], "reason": {"a": 1}}, headers=tok("gestor")),
        c.post("/nba/C000001'; DROP TABLE ops.audit_log;--/aprovacao", json={"decision": "approve", "reason": "motivo suficiente"}, headers=tok("gestor")),
        c.get("/clientes/C000001'%20OR%20'1'='1", headers=tok("analista")),
        c.get("/clientes", params={"sort": "hvs; DROP TABLE x", "segment": "' OR 1=1 --"}, headers=tok("analista")),
        c.get("/audit", params={"offset": -1}, headers=tok("auditor")),
    ]
    for r in hostile:
        assert r.status_code in (404, 422), (r.status_code, r.text[:200])
        assert "psycopg" not in r.text and "Traceback" not in r.text and "ops.audit_log" not in r.text.replace("DROP TABLE ops.audit_log", "")
    assert c.get("/audit", params={"entity_id": need}, headers=tok("auditor")).json()["total"] == 0
    assert c.get("/audit", headers=tok("auditor")).status_code == 200  # tabela intacta
