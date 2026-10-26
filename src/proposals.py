"""Persistencia das propostas do agente (ops.agent_proposals) com trilha em ops.audit_log.

O agente apenas propoe: nao existe caminho de codigo que "ative" algo. A decisao e humana e registrada no audit_log.
"""
from __future__ import annotations

from typing import Literal

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

PROPOSAL_ENTITY = "agent_proposal"
CUSTOMER_ID_PATTERN = r"^C\d{6}$"
COLUMNS = ("proposal_id::text AS proposal_id, created_at, customer_id, action, expected_margin_brl::float8 AS expected_margin_brl, rationale, "
           "sources, guardrails, provider, simulated, status, requested_by, request_id, decided_by, decided_at, decision_reason")


class ProposalIn(BaseModel):
    customer_id: str = Field(pattern=CUSTOMER_ID_PATTERN)
    action: str = Field(min_length=1, max_length=200)
    expected_margin_brl: float = Field(ge=0)
    rationale: str = Field(min_length=1, max_length=2000)
    sources: list[dict] = Field(default_factory=list)
    guardrails: dict = Field(default_factory=dict)
    provider: Literal["rules", "llm"] = "rules"


class ProposalConflict(Exception):
    """Ja existe proposta pendente para o cliente, ou a proposta ja foi decidida."""


class ProposalNotFound(Exception):
    pass


def _audit(conn: psycopg.Connection, actor: str, role: str, action: str, proposal_id: str, before: dict | None, after: dict, request_id: str | None) -> int:
    return conn.execute(
        """INSERT INTO ops.audit_log (actor, actor_role, action, entity, entity_id, before, after, request_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (actor, role, action, PROPOSAL_ENTITY, proposal_id, Jsonb(before) if before is not None else None, Jsonb(after), request_id)).fetchone()["id"]


def create_proposal(conn: psycopg.Connection, proposal: ProposalIn, actor: str, role: str, request_id: str | None = None) -> dict:
    """Grava a proposta (status pending) e o evento proposal.create na mesma transacao."""
    with conn.transaction():
        try:
            with conn.transaction():
                row = conn.execute(
                    f"""INSERT INTO ops.agent_proposals (customer_id, action, expected_margin_brl, rationale, sources, guardrails, provider, requested_by, request_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING {COLUMNS}""",
                    (proposal.customer_id, proposal.action, proposal.expected_margin_brl, proposal.rationale, Jsonb(proposal.sources),
                     Jsonb(proposal.guardrails), proposal.provider, actor, request_id)).fetchone()
        except psycopg.errors.UniqueViolation:
            raise ProposalConflict("Ja existe proposta pendente para este cliente") from None
        _audit(conn, actor, role, "proposal.create", row["proposal_id"], None, {"status": "pending", "customer_id": row["customer_id"], "action": row["action"],
                                                                                  "expected_margin_brl": row["expected_margin_brl"], "provider": row["provider"]}, request_id)
    return row


def decide_proposal(conn: psycopg.Connection, proposal_id: str, decision: Literal["approve", "reject"], reason: str, actor: str, role: str,
                    request_id: str | None = None) -> dict:
    """Aprova/rejeita uma proposta pendente; atualiza o estado e grava before/after no audit_log (mesma transacao)."""
    status = "approved" if decision == "approve" else "rejected"
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"{PROPOSAL_ENTITY}:{proposal_id}",))
        current = conn.execute("SELECT status FROM ops.agent_proposals WHERE proposal_id = %s::uuid", (proposal_id,)).fetchone()
        if current is None:
            raise ProposalNotFound(proposal_id)
        if current["status"] != "pending":
            raise ProposalConflict(f"Proposta ja decidida ({current['status']})")
        row = conn.execute(
            f"""UPDATE ops.agent_proposals SET status = %s, decided_by = %s, decided_at = now(), decision_reason = %s
                WHERE proposal_id = %s::uuid RETURNING {COLUMNS}""", (status, actor, reason, proposal_id)).fetchone()
        _audit(conn, actor, role, f"proposal.{decision}", proposal_id, {"status": "pending"}, {"status": status, "reason": reason}, request_id)
    return row
