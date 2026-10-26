"""Login de demonstracao: desligado por padrao (404), 1 token por perfil quando DEMO_LOGIN=1, token valido com o RBAC real."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.security import ISSUER
import jwt

SECRET = "unit-test-secret-" + "z" * 32


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.delenv("DEMO_LOGIN", raising=False)
    app.state.limiter.reset()
    return TestClient(app)


def test_demo_is_disabled_by_default(client):
    assert client.get("/auth/demo").json() == {"enabled": False}
    for role in ("analista", "gestor", "auditor"):
        assert client.post(f"/auth/demo/{role}").status_code == 404


@pytest.mark.parametrize("value", ["0", "true", "yes", ""])
def test_only_exact_flag_enables_demo(client, monkeypatch, value):
    monkeypatch.setenv("DEMO_LOGIN", value)
    assert client.get("/auth/demo").json() == {"enabled": False}
    assert client.post("/auth/demo/gestor").status_code == 404


@pytest.mark.parametrize("role", ["analista", "gestor", "auditor"])
def test_demo_token_per_role_is_short_lived_and_usable(client, monkeypatch, role):
    monkeypatch.setenv("DEMO_LOGIN", "1")
    assert client.get("/auth/demo").json() == {"enabled": True}
    body = client.post(f"/auth/demo/{role}").json()
    claims = jwt.decode(body["token"], SECRET, algorithms=["HS256"], issuer=ISSUER)
    assert claims["role"] == role and claims["sub"] == f"demo.{role}" and claims["exp"] - claims["iat"] == 3600 == body["expires_in"]
    headers = {"Authorization": f"Bearer {body['token']}"}
    # RBAC real (checado antes de qualquer acesso ao banco): so o gestor decide; o auditor nao usa o agente
    uid = "00000000-0000-0000-0000-000000000000"
    if role == "analista":
        assert client.post(f"/propostas/{uid}/decisao", json={"decision": "approve", "reason": "teste demo"}, headers=headers).status_code == 403
    if role == "auditor":
        assert client.post("/agente/perguntar", json={"question": "niveis do programa"}, headers=headers).status_code == 403


def test_demo_rejects_unknown_role_and_weak_secret(client, monkeypatch):
    monkeypatch.setenv("DEMO_LOGIN", "1")
    assert client.post("/auth/demo/root").status_code == 422
    monkeypatch.setenv("JWT_SECRET", "curto")
    assert client.post("/auth/demo/gestor").status_code == 503
