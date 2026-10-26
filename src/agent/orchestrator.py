"""Orquestracao do agente: plano fixo de ferramentas (sem o LLM escolher), redacao pelo provider e fallback por regras.

A acao proposta sai exclusivamente de `calcular_elegibilidade`; o LLM, se houver, apenas redige o texto.
Os logs registram so metadados (ferramentas, provider, latencia), nunca pergunta, resposta ou conteudo de fonte.
"""
from __future__ import annotations

import logging
import re
import time

import psycopg

from ..knowledge.embeddings import Embedder
from .providers import AgentContext, LLMProvider, ProviderError, RulesProvider, resolve_provider
from .schemas import AgentAnswer, Citation, ProposedAction
from .tools import ToolError, Toolbox, content_query

log = logging.getLogger("agent")
CUSTOMER_ID = re.compile(r"\bC\d{6}\b")


class Agent:
    def __init__(self, conn: psycopg.Connection, provider: LLMProvider | None = None, config_fallback: str | None = None, embedder: Embedder | None = None):
        self.tools = Toolbox(conn, embedder)
        if provider is None:
            provider, config_fallback = resolve_provider()
        self.provider, self.config_fallback = provider, config_fallback

    def _gather(self, question: str) -> tuple[AgentContext, list[str]]:
        ctx, used = AgentContext(), []
        match = CUSTOMER_ID.search(question)
        if match:
            for name, attr in (("consultar_cliente", "customer"), ("calcular_elegibilidade", "eligibility")):
                try:
                    setattr(ctx, attr, self.tools.call(name, {"customer_id": match.group()}))
                    used.append(name)
                except ToolError as exc:
                    ctx.errors.append(f"{name}: {exc}")
        try:
            ctx.hits = self.tools.call("buscar_regra", {"query": content_query(CUSTOMER_ID.sub(" ", question)), "k": 3}).hits
            used.append("buscar_regra")
        except ToolError as exc:
            ctx.errors.append(f"buscar_regra: {exc}")
        return ctx, used

    def ask(self, question: str) -> AgentAnswer:
        started = time.perf_counter()
        ctx, used = self._gather(question)
        fallback_reason = self.config_fallback
        try:
            text, provider_name = self.provider.draft(question, ctx), self.provider.name
        except ProviderError as exc:
            text, provider_name, fallback_reason = RulesProvider().draft(question, ctx), "rules", exc.reason
        proposal = None
        if ctx.customer and ctx.eligibility and ctx.eligibility.best_expected_margin_brl > 0:
            proposal = ProposedAction(customer_id=ctx.customer.customer_id, action=ctx.eligibility.best_action,
                                      expected_margin_brl=ctx.eligibility.best_expected_margin_brl, requires_approval=True)
        citations = [Citation(ref=i, url=h.url, title=h.title, version=h.version, consulted_at=h.consulted_at, section=h.section, score=h.score)
                     for i, h in enumerate(ctx.hits, 1)]
        log.info("agent_answer", extra={"tools": used, "provider": provider_name, "fallback_reason": fallback_reason, "citations": len(citations),
                                        "latency_ms": round((time.perf_counter() - started) * 1000, 1)})
        return AgentAnswer(answer=text, customer_id=ctx.customer.customer_id if ctx.customer else None, proposed_action=proposal, citations=citations,
                           tools_used=used, provider=provider_name, fallback_used=fallback_reason is not None, fallback_reason=fallback_reason)
