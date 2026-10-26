"""Endpoints do agente (SSE) e da fila de aprovacao de propostas.

O agente so propoe: a resposta e validada pelos guardrails ANTES de ser transmitida (nenhum token nao validado sai da API) e a ativacao
continua dependendo de decisao humana em POST /propostas/{id}/decisao (somente gestor), que grava em ops.audit_log.
EventSource nao envia Authorization; o cliente deve usar fetch com leitura de stream.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections.abc import Iterator
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.responses import StreamingResponse
from psycopg.rows import dict_row

from ..agent.orchestrator import Agent
from ..agent.schemas import AgentAnswer, AskRequest
from ..proposals import COLUMNS as PROPOSAL_COLUMNS
from ..proposals import ProposalConflict, ProposalIn, ProposalNotFound, create_proposal, decide_proposal
from .deps import AuditConn, Conn
from .models import ApprovalRequest, ProposalOut
from .security import Principal, require

CUSTOMER_ID_PATTERN = r"^C\d{6}$"
CHUNK_CHARS = 40
QUEUE_POLL_SECONDS = 2.0
QUEUE_MAX_SECONDS = 60.0  # o cliente reconecta; evita conexao eterna
MAX_QUEUE_STREAMS = 10
_streams = threading.BoundedSemaphore(MAX_QUEUE_STREAMS)
SSE_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
router = APIRouter()
STAFF = require("analista", "gestor")


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _chunks(text: str) -> Iterator[str]:
    words, buf = text.split(" "), ""
    for w in words:
        if buf and len(buf) + len(w) + 1 > CHUNK_CHARS:
            yield buf + " "
            buf = w
        else:
            buf = f"{buf} {w}" if buf else w
    if buf:
        yield buf


def answer_events(answer: AgentAnswer, proposal: dict | None = None) -> Iterator[str]:
    yield sse("meta", {"simulated": answer.simulated, "notice": answer.notice, "provider": answer.provider, "fallback_used": answer.fallback_used,
                       "fallback_reason": answer.fallback_reason, "tools_used": answer.tools_used})
    yield sse("guardrails", answer.guardrails.model_dump())
    yield sse("sources", [c.model_dump() for c in answer.citations])
    if answer.proposed_action:
        yield sse("proposed_action", answer.proposed_action.model_dump())
    for part in _chunks(answer.answer):
        yield sse("delta", {"text": part})
    if proposal is not None:
        yield sse("proposal", ProposalOut(**proposal).model_dump(mode="json"))
    yield sse("done", answer.model_dump())


def stream_response(events: Iterator[str]) -> StreamingResponse:
    return StreamingResponse(events, media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/agente/perguntar", summary="Pergunta ao agente (SSE; simulado, nunca ativa nada)", response_class=StreamingResponse,
             responses={200: {"content": {"text/event-stream": {}}}})
def ask(_: Annotated[Principal, Depends(STAFF)], body: AskRequest, conn: Conn):
    answer = Agent(conn).ask(body.question)  # validado pelos guardrails antes de qualquer byte ser enviado
    return stream_response(answer_events(answer))


@router.post("/nba/{customer_id}/proposta", summary="Gera e persiste uma proposta do agente para o cliente (SSE; pendente de aprovacao humana)",
             response_class=StreamingResponse, responses={200: {"content": {"text/event-stream": {}}}})
def propose(principal: Annotated[Principal, Depends(STAFF)], request: Request, customer_id: Annotated[str, PathParam(pattern=CUSTOMER_ID_PATTERN)],
            conn: Conn, audit: AuditConn):
    answer = Agent(conn).ask(f"Qual a melhor acao para {customer_id} considerando os niveis do programa?")
    if answer.guardrails.status == "blocked":
        raise HTTPException(status_code=422, detail="Resposta bloqueada pelos guardrails; nenhuma proposta criada")
    if answer.customer_id is None:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    if answer.proposed_action is None:
        raise HTTPException(status_code=409, detail="Nenhuma acao elegivel com margem esperada positiva")
    p = answer.proposed_action
    try:
        row = create_proposal(
            audit, ProposalIn(customer_id=p.customer_id, action=p.action, expected_margin_brl=max(p.expected_margin_brl, 0.0), rationale=answer.answer[:2000],
                              sources=[c.model_dump() for c in answer.citations], guardrails=answer.guardrails.model_dump(), provider=answer.provider),
            principal.sub, principal.role, getattr(request.state, "request_id", None))
    except ProposalConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return stream_response(answer_events(answer, row))


@router.post("/propostas/{proposal_id}/decisao", response_model=ProposalOut, status_code=201,
             summary="Aprova ou rejeita uma proposta do agente (somente gestor); grava before/after em ops.audit_log")
def decide(principal: Annotated[Principal, Depends(require("gestor"))], request: Request, proposal_id: uuid.UUID, body: ApprovalRequest, audit: AuditConn):
    try:
        return decide_proposal(audit, str(proposal_id), body.decision, body.reason, principal.sub, principal.role, getattr(request.state, "request_id", None))
    except ProposalNotFound:
        raise HTTPException(status_code=404, detail="Proposta nao encontrada") from None
    except ProposalConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


def _queue_events(dsn: str) -> Iterator[str]:
    if not _streams.acquire(blocking=False):  # adquirido dentro do gerador: o release no finally nunca vaza
        yield sse("error", {"detail": "Muitas conexoes de streaming abertas"})
        return
    deadline, last, polls = time.monotonic() + QUEUE_MAX_SECONDS, None, 0
    try:
        with psycopg.connect(dsn, row_factory=dict_row, autocommit=True, options="-c default_transaction_read_only=on") as conn:
            while True:
                rows = conn.execute(f"SELECT {PROPOSAL_COLUMNS} FROM ops.agent_proposals WHERE status = 'pending' ORDER BY created_at DESC LIMIT 100").fetchall()
                key = sorted(r["proposal_id"] for r in rows)
                if key != last:
                    last = key
                    yield sse("queue", {"pending": len(rows), "items": [ProposalOut(**r).model_dump(mode="json") for r in rows]})
                elif polls % 5 == 0:
                    yield ": keepalive\n\n"
                polls += 1
                if time.monotonic() >= deadline:
                    yield sse("end", {"reconnect": True})
                    return
                time.sleep(QUEUE_POLL_SECONDS)
    except psycopg.Error:
        yield sse("error", {"detail": "Banco indisponivel"})
    finally:
        _streams.release()


@router.get("/propostas/fila/stream", summary="Fila de propostas pendentes em tempo real (SSE; reconecte ao receber 'end')", dependencies=[Depends(require("analista", "gestor", "auditor"))],
            response_class=StreamingResponse, responses={200: {"content": {"text/event-stream": {}}}})
def queue_stream():
    dsn = os.environ.get("DATABASE_URL_RO")
    if not dsn:
        raise HTTPException(status_code=503, detail="Banco nao configurado")
    return stream_response(_queue_events(dsn))
