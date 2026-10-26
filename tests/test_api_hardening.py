"""Seguranca basica da API sem banco: cobertura de rotas, metodos, erros genericos e limites (complementa test_api_security)."""
import re

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, create_app
from src.api.security import issue_token

SECRET = "hardening-test-secret-" + "k" * 32


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    app.state.limiter.reset()


def bearer(role="gestor"):
    return {"Authorization": f"Bearer {issue_token('tester', role, secret=SECRET)}"}


def openapi_operations():
    for path, item in app.openapi()["paths"].items():
        for method in item:
            yield method.upper(), re.sub(r"\{[^}]+\}", "C000001", path)


def test_every_documented_operation_requires_a_token():
    """Se alguem adicionar uma rota sem dependencia de autenticacao, este teste quebra."""
    ops = list(openapi_operations())
    assert len(ops) >= 12
    c = TestClient(app)
    open_ops = [(m, p) for m, p in ops if not p.startswith("/auth/demo") and c.request(m, p, json={} if m == "POST" else None).status_code != 401]
    assert open_ops == []
    # login de demo: publico por desenho, mas 404 enquanto DEMO_LOGIN != 1
    assert c.get("/auth/demo").json() == {"enabled": False} and c.post("/auth/demo/gestor").status_code in (404, 503)


def test_health_is_the_only_undocumented_public_route():
    paths = app.openapi()["paths"]
    assert "/health" not in paths
    assert TestClient(app).get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("method,path", [("DELETE", "/nba/C000001/aprovacao"), ("PUT", "/nba/C000001/aprovacao"), ("PUT", "/kpis"), ("DELETE", "/clientes/C000001"), ("POST", "/audit"), ("PATCH", "/ops/runs")])
def test_unsupported_methods_are_405(method, path):
    assert TestClient(app).request(method, path, headers=bearer("gestor")).status_code == 405


def test_unknown_path_returns_generic_404():
    r = TestClient(app).get("/admin/../etc/passwd", headers=bearer())
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}


def test_database_failure_does_not_leak_dsn_or_password(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_RO", "postgresql://fidelidade_ro:change-me-canary@127.0.0.1:1/fidelidade?connect_timeout=1")
    r = TestClient(app, raise_server_exceptions=False).get("/kpis", headers=bearer("analista"))
    assert r.status_code >= 500
    text = r.text + str(dict(r.headers))
    for leak in ("change-me-canary", "fidelidade_ro", "127.0.0.1", "Traceback", "psycopg"):
        assert leak not in text


def test_forwarded_for_cannot_bypass_rate_limit(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    monkeypatch.delenv("DATABASE_URL_RO", raising=False)
    c = TestClient(create_app())
    codes = [c.get("/kpis", headers={**bearer("analista"), "X-Forwarded-For": f"10.0.0.{i}"}).status_code for i in range(5)]
    assert codes[3:] == [429, 429]


def test_rate_limit_applies_before_authentication(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    c = TestClient(create_app())
    codes = [c.get("/kpis").status_code for _ in range(4)]
    assert codes == [401, 401, 429, 429]


def test_write_bucket_is_stricter_than_read(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "100")
    monkeypatch.setenv("RATE_LIMIT_WRITE_PER_MINUTE", "2")
    c = TestClient(create_app())
    codes = [c.post("/nba/C000001/aprovacao", json={}).status_code for _ in range(4)]
    assert codes == [401, 401, 429, 429]


def test_cors_preflight_does_not_allow_foreign_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    c = TestClient(create_app())
    ok = c.options("/kpis", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    bad = c.options("/kpis", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers
