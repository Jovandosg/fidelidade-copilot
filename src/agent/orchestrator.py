"""Orquestracao do agente: guardrails de entrada, plano fixo de ferramentas (sem o LLM escolher), redacao pelo provider,
guardrails de saida e fallback por regras.

A acao proposta sai exclusivamente de `calcular_elegibilidade` e sempre exige aprovacao humana; o LLM, se houver, apenas redige o texto.
Os logs registram so metadados (ferramentas, provider, codigos de guardrail, latencia), nunca pergunta, resposta ou conteudo de fonte.
"""
from __future__ import annotations

import logging
import re
import time

import psycopg

from ..knowledge.embeddings import Embedder
from .guardrails import CHECKS, check_input, check_output, detect_injection
from .providers import AgentContext, LLMProvider, ProviderError, RulesProvider, resolve_provider
from .schemas import AgentAnswer, Citation, GuardrailReport, ProposedAction
from .tools import ToolError, Toolbox, content_query

log = logging.getLogger("agent")
CUSTOMER_ID = re.compile(r"\bC\d{6}\b")
REFUSAL = "Nao posso atender a esta solicitacao. O agente apenas consulta, explica e propoe acoes com fonte; nenhuma acao e ativada sem aprovacao humana."
SAFE_FALLBACK = "Nao consegui gerar uma resposta que cumpra as politicas de seguranca; encaminhe a pergunta a um analista."


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
            hits = self.tools.call("buscar_regra", {"query": content_query(CUSTOMER_ID.sub(" ", question)), "k": 3}).hits
            ctx.hits = [h for h in hits if not detect_injection(h.content)]  # defesa em profundidade: fonte com instrucoes nunca vira contexto
            used.append("buscar_regra")
        except ToolError as exc:
            ctx.errors.append(f"buscar_regra: {exc}")
        return ctx, used

    @staticmethod
    def _build(text: str, provider: str, fallback_reason: str | None, ctx: AgentContext, used: list[str], report: GuardrailReport) -> AgentAnswer:
        proposal = None
        if ctx.customer and ctx.eligibility and ctx.eligibility.best_expected_margin_brl > 0:
            proposal = ProposedAction(customer_id=ctx.customer.customer_id, action=ctx.eligibility.best_action,
                                      expected_margin_brl=ctx.eligibility.best_expected_margin_brl)
        citations = [Citation(ref=i, url=h.url, title=h.title, version=h.version, consulted_at=h.consulted_at, section=h.section, score=h.score)
                     for i, h in enumerate(ctx.hits, 1)]
        return AgentAnswer(answer=text, customer_id=ctx.customer.customer_id if ctx.customer else None, proposed_action=proposal, citations=citations,
                           tools_used=used, provider=provider, fallback_used=fallback_reason is not None, fallback_reason=fallback_reason, guardrails=report)

    @staticmethod
    def _refusal(text: str, report: GuardrailReport) -> AgentAnswer:
        report.status = "blocked"
        return AgentAnswer(answer=text, customer_id=None, proposed_action=None, citations=[], tools_used=[], provider="rules", fallback_used=False, guardrails=report)

    def ask(self, question: str) -> AgentAnswer:
        started = time.perf_counter()
        verdict = check_input(question)
        report = GuardrailReport(input_flags=verdict.flags, checks=["input", *CHECKS])
        if not verdict.allowed:
            log.info("agent_blocked", extra={"flags": verdict.flags})
            return self._refusal(REFUSAL, report)

        ctx, used = self._gather(verdict.sanitized)
        fallback_reason = self.config_fallback
        try:
            text, provider_name = self.provider.draft(verdict.sanitized, ctx), self.provider.name
        except ProviderError as exc:
            text, provider_name, fallback_reason = RulesProvider().draft(verdict.sanitized, ctx), "rules", exc.reason
        answer = self._build(text, provider_name, fallback_reason, ctx, used, report)

        violations = check_output(answer, ctx)
        if violations and provider_name != "rules":
            report.output_violations = violations
            report.status = "fallback"
            answer = self._build(RulesProvider().draft(verdict.sanitized, ctx), "rules", "guardrail_violation", ctx, used, report)
            violations = check_output(answer, ctx)
        if violations:
            report.output_violations = list(dict.fromkeys([*report.output_violations, *violations]))
            answer = self._refusal(SAFE_FALLBACK, report)
        log.info("agent_answer", extra={"tools": used, "provider": answer.provider, "fallback_reason": answer.fallback_reason, "guardrail_status": report.status,
                                        "violations": report.output_violations, "citations": len(answer.citations),
                                        "latency_ms": round((time.perf_counter() - started) * 1000, 1)})
        return answer
