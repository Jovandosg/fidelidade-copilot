"""Saude da plataforma (ops.*), trilha de auditoria e aprovacao de NBA."""
from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import Path as PathParam
from psycopg.types.json import Jsonb

from .deps import AuditConn, Conn
from .models import (ApprovalRequest, ApprovalResult, ApprovalStatus, AuditEntry, AuditPage, DriftReport, ModelOut, PipelineRunOut, ProposalOut, QualityOut)
from .security import Principal, require
from ..proposals import COLUMNS as PROPOSAL_COLUMNS

CUSTOMER_ID_PATTERN = r"^C\d{6}$"
NBA_ENTITY = "nba_recommendation"
ALL_ROLES = require("analista", "gestor", "auditor")
router = APIRouter()


@router.get("/ops/runs", response_model=list[PipelineRunOut], summary="Execucoes do pipeline", dependencies=[Depends(ALL_ROLES)])
def runs(conn: Conn, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return conn.execute(
        """SELECT run_id::text AS run_id, started_at, finished_at, duration_ms, status, code_version, seed, contract_version, rows_by_entity, error
           FROM ops.pipeline_runs ORDER BY started_at DESC LIMIT %s""", (limit,)).fetchall()


@router.get("/ops/quality", response_model=QualityOut, summary="Qualidade por regra (ultima execucao ou run_id)", dependencies=[Depends(ALL_ROLES)])
def quality(conn: Conn, run_id: uuid.UUID | None = None):
    if run_id is None:
        row = conn.execute("""SELECT r.run_id FROM ops.pipeline_runs r WHERE EXISTS (SELECT 1 FROM ops.data_quality_results q WHERE q.run_id = r.run_id)
                              ORDER BY r.started_at DESC LIMIT 1""").fetchone()
        run_id = row["run_id"] if row else None
    rows = conn.execute("SELECT entity, rule, passed, failed_rows FROM ops.data_quality_results WHERE run_id = %s ORDER BY passed, entity, rule",
                        (run_id,)).fetchall() if run_id else []
    return QualityOut(run_id=str(run_id) if run_id else None, total_rules=len(rows), failed_rules=sum(not r["passed"] for r in rows), results=rows)


@router.get("/ops/models", response_model=list[ModelOut], summary="Registro de modelos (metricas sobre dados sinteticos)", dependencies=[Depends(ALL_ROLES)])
def models(conn: Conn):
    return conn.execute(
        """SELECT model_name, model_version, run_id::text AS run_id, trained_at, data_hash, metrics, params, synthetic_notice
           FROM ops.model_registry ORDER BY trained_at DESC, model_name""").fetchall()


@router.get("/ops/drift", response_model=DriftReport, summary="PSI por feature (ultima execucao com drift ou run_id)", dependencies=[Depends(ALL_ROLES)])
def drift(conn: Conn, run_id: uuid.UUID | None = None):
    if run_id is None:
        row = conn.execute("SELECT run_id FROM ops.drift_metrics ORDER BY computed_at DESC, id DESC LIMIT 1").fetchone()
        run_id = row["run_id"] if row else None
    rows = conn.execute("SELECT feature, psi::float8 AS psi, threshold::float8 AS threshold, alert, computed_at FROM ops.drift_metrics "
                        "WHERE run_id = %s ORDER BY psi DESC, feature", (run_id,)).fetchall() if run_id else []
    return DriftReport(run_id=str(run_id) if run_id else None, computed_at=rows[0]["computed_at"] if rows else None,
                       alerts=sum(r["alert"] for r in rows), items=rows)


@router.get("/audit", response_model=AuditPage, summary="Trilha de auditoria (somente auditor)")
def audit(_: Annotated[Principal, Depends(require("auditor"))], conn: AuditConn, limit: Annotated[int, Query(ge=1, le=200)] = 50,
          offset: Annotated[int, Query(ge=0)] = 0, entity_id: Annotated[str | None, Query(pattern=CUSTOMER_ID_PATTERN)] = None):
    where, params = ("WHERE entity_id = %s", (entity_id,)) if entity_id else ("", ())
    total = conn.execute(f"SELECT count(*) AS n FROM ops.audit_log {where}", params).fetchone()["n"]
    items = conn.execute(f"SELECT id, occurred_at, actor, actor_role, action, entity, entity_id, before, after, request_id FROM ops.audit_log {where} "
                         "ORDER BY id DESC LIMIT %s OFFSET %s", (*params, limit, offset)).fetchall()
    return AuditPage(total=total, limit=limit, offset=offset, items=[AuditEntry(**i) for i in items])


@router.get("/propostas", response_model=list[ProposalOut], summary="Propostas do agente persistidas (simuladas; exigem aprovacao humana)",
            dependencies=[Depends(ALL_ROLES)])
def proposals(conn: Conn, status: Annotated[Literal["pending", "approved", "rejected"] | None, Query()] = None,
              customer_id: Annotated[str | None, Query(pattern=CUSTOMER_ID_PATTERN)] = None, limit: Annotated[int, Query(ge=1, le=200)] = 50):
    return conn.execute(
        f"""SELECT {PROPOSAL_COLUMNS} FROM ops.agent_proposals WHERE (%(s)s::text IS NULL OR status = %(s)s) AND (%(c)s::text IS NULL OR customer_id = %(c)s)
            ORDER BY created_at DESC LIMIT %(l)s""", {"s": status, "c": customer_id, "l": limit}).fetchall()


@router.get("/propostas/{proposal_id}", response_model=ProposalOut, summary="Detalhe de uma proposta do agente", dependencies=[Depends(ALL_ROLES)])
def proposal(proposal_id: uuid.UUID, conn: Conn):
    row = conn.execute(f"SELECT {PROPOSAL_COLUMNS} FROM ops.agent_proposals WHERE proposal_id = %s", (proposal_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Proposta nao encontrada")
    return row


@router.get("/nba/aprovacoes", response_model=list[ApprovalStatus], summary="Decisoes de aprovacao vigentes (gestor e auditor)",
            dependencies=[Depends(require("gestor", "auditor"))])
def approvals(conn: AuditConn):
    rows = conn.execute(
        """SELECT DISTINCT ON (entity_id) entity_id AS customer_id, substr(action, 5) AS decision, actor, occurred_at
           FROM ops.audit_log WHERE entity = %s AND action IN ('nba.approve', 'nba.reject') ORDER BY entity_id, id DESC""", (NBA_ENTITY,)).fetchall()
    conn.rollback()
    return rows


@router.post("/nba/{customer_id}/aprovacao", response_model=ApprovalResult, status_code=201,
             summary="Aprova ou rejeita uma acao NBA (somente gestor); grava em ops.audit_log")
def decide(principal: Annotated[Principal, Depends(require("gestor"))], request: Request,
           customer_id: Annotated[str, PathParam(pattern=CUSTOMER_ID_PATTERN)], body: ApprovalRequest, conn: AuditConn):
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"{NBA_ENTITY}:{customer_id}",))  # serializa decisoes concorrentes do mesmo cliente
        row = conn.execute("SELECT nba_action, nba_expected_margin_brl::float8 AS margin, nba_requires_approval FROM analytics.customer_features "
                           "WHERE customer_id = %s", (customer_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")
        if not row["nba_requires_approval"]:
            raise HTTPException(status_code=409, detail="Esta acao nao exige aprovacao humana")
        if conn.execute("SELECT 1 FROM ops.audit_log WHERE entity = %s AND entity_id = %s AND action IN ('nba.approve', 'nba.reject') LIMIT 1",
                        (NBA_ENTITY, customer_id)).fetchone():
            raise HTTPException(status_code=409, detail="Ja existe decisao para este cliente (a trilha e imutavel)")
        snapshot = {"nba_action": row["nba_action"], "nba_expected_margin_brl": row["margin"]}
        before = {**snapshot, "approval_status": "pending"}
        after = {**snapshot, "approval_status": "approved" if body.decision == "approve" else "rejected", "reason": body.reason}
        saved = conn.execute(
            """INSERT INTO ops.audit_log (actor, actor_role, action, entity, entity_id, before, after, request_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id, occurred_at""",
            (principal.sub, principal.role, f"nba.{body.decision}", NBA_ENTITY, customer_id, Jsonb(before), Jsonb(after),
             getattr(request.state, "request_id", None))).fetchone()
    return ApprovalResult(audit_id=saved["id"], occurred_at=saved["occurred_at"], customer_id=customer_id, decision=body.decision, before=before, after=after)
