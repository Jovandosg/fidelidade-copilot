"""Persistencia das propostas do agente: tabela, maquina de estados, privilegios, audit_log e leitura via API (banco temporario)."""
import os
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from src import db
from src.api.main import app
from src.api.security import issue_token
from src.proposals import ProposalConflict, ProposalIn, ProposalNotFound, create_proposal, decide_proposal

DSN, DSN_RO, DSN_AUDIT = (os.environ.get(v) for v in ("DATABASE_URL", "DATABASE_URL_RO", "DATABASE_URL_AUDIT"))
needs_db = pytest.mark.skipif(not (DSN and DSN_RO and DSN_AUDIT), reason="DATABASE_URL, _RO e _AUDIT nao definidos")
SECRET = "unit-test-secret-" + "y" * 32


def tok(role="analista", sub="tester"):
    return {"Authorization": f"Bearer {issue_token(sub, role, secret=SECRET)}"}


def sample(cid="C000001", **over):
    return ProposalIn(**{"customer_id": cid, "action": "Oferta de retencao", "expected_margin_brl": 120.5, "rationale": "Regra publica de retencao",
                         "sources": [{"url": "https://example.org/regra", "consulted_at": "2026-10-25"}], "guardrails": {"passed": True}, **over})


@pytest.fixture(scope="module")
def live():
    name = f"fidelidade_prop_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    with psycopg.connect(make_conninfo(DSN, dbname=name)) as owner:
        db.migrate(owner)
        owner.commit()
    mp = pytest.MonkeyPatch()
    mp.setenv("DATABASE_URL_RO", make_conninfo(DSN_RO, dbname=name))
    mp.setenv("DATABASE_URL_AUDIT", make_conninfo(DSN_AUDIT, dbname=name))
    mp.setenv("JWT_SECRET", SECRET)
    try:
        yield name
    finally:
        mp.undo()
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


@pytest.fixture()
def audit_conn(live):
    with psycopg.connect(make_conninfo(DSN_AUDIT, dbname=live), row_factory=dict_row, autocommit=True) as conn:
        yield conn


@pytest.fixture(autouse=True)
def _limiter(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    app.state.limiter.reset()


@needs_db
def test_create_persists_pending_proposal_and_audit_event(live, audit_conn):
    row = create_proposal(audit_conn, sample("C000010"), "agente.sistema", "analista", "req-1")
    assert row["status"] == "pending" and row["simulated"] is True and row["decided_by"] is None and row["provider"] == "rules"
    ev = audit_conn.execute("SELECT actor, action, entity, entity_id, before, after, request_id FROM ops.audit_log WHERE entity_id = %s", (row["proposal_id"],)).fetchall()
    assert [(e["action"], e["entity"], e["request_id"], e["before"]) for e in ev] == [("proposal.create", "agent_proposal", "req-1", None)]
    assert ev[0]["after"]["status"] == "pending"


@needs_db
def test_one_pending_proposal_per_customer_and_decision_flow(live, audit_conn):
    first = create_proposal(audit_conn, sample("C000020"), "agente.sistema", "analista")
    with pytest.raises(ProposalConflict):
        create_proposal(audit_conn, sample("C000020"), "agente.sistema", "analista")
    decided = decide_proposal(audit_conn, first["proposal_id"], "approve", "Dentro da politica", "maria.gestora", "gestor", "req-2")
    assert decided["status"] == "approved" and decided["decided_by"] == "maria.gestora" and decided["decided_at"] and decided["decision_reason"] == "Dentro da politica"
    with pytest.raises(ProposalConflict):
        decide_proposal(audit_conn, first["proposal_id"], "reject", "mudei de ideia", "maria.gestora", "gestor")
    with pytest.raises(ProposalNotFound):
        decide_proposal(audit_conn, str(uuid.uuid4()), "reject", "inexistente", "maria.gestora", "gestor")
    actions = [e["action"] for e in audit_conn.execute("SELECT action FROM ops.audit_log WHERE entity_id = %s ORDER BY id", (first["proposal_id"],)).fetchall()]
    assert actions == ["proposal.create", "proposal.approve"]
    second = create_proposal(audit_conn, sample("C000020"), "agente.sistema", "analista")  # apos decidida, pode haver nova proposta
    assert second["proposal_id"] != first["proposal_id"]


@needs_db
def test_check_constraints_reject_invalid_rows(live, audit_conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        audit_conn.execute("INSERT INTO ops.agent_proposals (customer_id, action, expected_margin_brl, rationale, provider, requested_by) VALUES ('C000030', 'x', -1, 'y', 'rules', 'a')")
    with pytest.raises(psycopg.errors.CheckViolation):
        audit_conn.execute("INSERT INTO ops.agent_proposals (customer_id, action, expected_margin_brl, rationale, provider, requested_by) "
                           "VALUES ('Maria Silva', 'x', 1, 'y', 'rules', 'a')")  # sem PII/formato livre: so ids sinteticos
    assert audit_conn.execute("SELECT count(*) AS n FROM ops.agent_proposals WHERE customer_id = 'C000030'").fetchone()["n"] == 0


@needs_db
def test_state_machine_and_privileges(live, audit_conn):
    row = create_proposal(audit_conn, sample("C000040"), "agente.sistema", "analista")
    pid = row["proposal_id"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        audit_conn.execute("UPDATE ops.agent_proposals SET rationale = 'adulterada' WHERE proposal_id = %s::uuid", (pid,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        audit_conn.execute("DELETE FROM ops.agent_proposals WHERE proposal_id = %s::uuid", (pid,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        audit_conn.execute("TRUNCATE ops.agent_proposals")
    with pytest.raises(psycopg.errors.CheckViolation):  # decidir exige decided_by/decided_at/motivo
        audit_conn.execute("UPDATE ops.agent_proposals SET status = 'approved' WHERE proposal_id = %s::uuid", (pid,))
    with psycopg.connect(make_conninfo(DSN_RO, dbname=live), autocommit=True) as ro:
        assert ro.execute("SELECT count(*) FROM ops.agent_proposals").fetchone()[0] >= 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            ro.execute("DELETE FROM ops.agent_proposals")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            ro.execute("INSERT INTO ops.agent_proposals (customer_id, action, expected_margin_brl, rationale, provider, requested_by) VALUES ('C000041','x',1,'y','rules','a')")
    decide_proposal(audit_conn, pid, "reject", "Fora da politica", "maria.gestora", "gestor")
    with psycopg.connect(make_conninfo(DSN, dbname=live), autocommit=True) as owner:  # trigger vale ate para o owner
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            owner.execute("UPDATE ops.agent_proposals SET status = 'approved' WHERE proposal_id = %s::uuid", (pid,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            owner.execute("DELETE FROM ops.agent_proposals WHERE proposal_id = %s::uuid", (pid,))


@needs_db
def test_api_reads_persisted_proposals(live, audit_conn):
    c = TestClient(app)
    row = create_proposal(audit_conn, sample("C000050"), "agente.sistema", "analista")
    for role in ("analista", "gestor", "auditor"):
        listing = c.get("/propostas", params={"customer_id": "C000050"}, headers=tok(role))
        assert listing.status_code == 200 and [p["proposal_id"] for p in listing.json()] == [row["proposal_id"]]
    detail = c.get(f"/propostas/{row['proposal_id']}", headers=tok()).json()
    assert detail["status"] == "pending" and detail["simulated"] is True and detail["sources"][0]["url"].startswith("https://")
    assert detail["expected_margin_brl"] == 120.5 and detail["guardrails"] == {"passed": True}
    decide_proposal(audit_conn, row["proposal_id"], "approve", "Aprovado pelo gestor", "maria.gestora", "gestor")
    assert [p["status"] for p in c.get("/propostas", params={"status": "approved", "customer_id": "C000050"}, headers=tok()).json()] == ["approved"]
    assert c.get("/propostas", params={"status": "pending", "customer_id": "C000050"}, headers=tok()).json() == []
    assert c.get(f"/propostas/{uuid.uuid4()}", headers=tok()).status_code == 404
    assert c.get("/propostas/nao-uuid", headers=tok()).status_code == 422
    assert c.get("/propostas", params={"status": "ativada"}, headers=tok()).status_code == 422
    assert c.get("/propostas", params={"customer_id": "Maria"}, headers=tok()).status_code == 422
    assert c.get("/propostas").status_code == 401
