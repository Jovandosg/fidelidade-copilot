"""Policy engine do agente: guardrails de entrada e de saida, deterministicos e sem LLM.

Entrada: sanitizacao, redacao de PII e deteccao de prompt injection (bloqueia antes de qualquer ferramenta).
Saida: JSON Schema, citacao obrigatoria de fonte publica, sem PII, teto de beneficio, elegibilidade e aprovacao humana.
Os relatorios guardam apenas codigos de regra, nunca trechos da pergunta ou da resposta.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlparse

import jsonschema

from ..models.nba import ACTIONS
from .providers import AgentContext
from .schemas import AgentAnswer

MAX_QUESTION_CHARS = 500
BENEFIT_CAP_BRL = max(cost for _, cost, _, _ in ACTIONS)  # teto = maior custo de acao do catalogo de premissas
ALLOWED_SOURCE_HOST = "voeazul.com.br"
ANSWER_SCHEMA = AgentAnswer.model_json_schema()

PII_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "telefone": re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b"),
}

INJECTION_PATTERNS = {
    "instruction_override": re.compile(
        r"\b(ignor\w*|desconsider\w*|esquec\w*|descart\w*|desobedec\w*)\b.{0,40}\b(regras?|instruc\w*|prompt|politicas?|diretriz\w*|anteriores|acima)\b"
        r"|\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|instructions?|rules?)\b"),
    "system_prompt": re.compile(r"system\s*prompt|(prompt|mensagem|instrucoes?)\s+(do\s+)?sistema"),
    "secret_exfiltration": re.compile(
        r"\b(revele|mostre|exiba|vaze|imprima|reveal|show|print|leak|repita)\b.{0,40}\b(prompt|instrucoes|chave|api.?key|senha|segredo|token|secret|credenciais?|variaveis? de ambiente)\b"),
    "role_hijack": re.compile(r"\byou\s+are\s+now\b|developer\s+mode|modo\s+desenvolvedor|jailbreak|\bdan\b|voce\s+(agora\s+)?(e|sera)\s+(um\s+)?(agente\s+)?(sem\s+restricoes|livre)"),
    "destructive_request": re.compile(r"\b(apague|apagar|delete|drop|truncate|altere|alterar|update|insert)\b.{0,30}\b(tabela|table|audit|log|banco|database)\b"),
    "sql_injection": re.compile(r"\b(select|union)\b.{0,40}\bfrom\b|;\s*(drop|delete|update|insert)\b|--\s*$"),
    "role_markup": re.compile(r"<\s*/?\s*(system|assistant|tool)\b|\[/?inst\]|<\|"),
    "activation_request": re.compile(
        r"\b(ative|ativar|ativa|execute|executar|aprove|aprovar|dispare|disparar|envie|enviar|credite|creditar)\b.{0,60}\b(oferta|acao|campanha|bonus|pontos|milhas|upgrade|cliente|c\d{6})\b"),
}
ACTIVATION_CLAIM = re.compile(r"\b(ativei|ativamos|foi ativad[oa]|ja ativad[oa]|executei|executamos|enviei|disparei|apliquei|creditei|aprovei|foi aprovad[oa]|foram creditad[oa]s?)\b")
CONTROL_CHARS = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
NO_SOURCE = "nao encontrei fonte"


def fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def detect_injection(text: str) -> list[str]:
    plain = fold(CONTROL_CHARS.sub("", unicodedata.normalize("NFKC", text)))
    return [label for label, pattern in INJECTION_PATTERNS.items() if pattern.search(plain)]


def detect_pii(text: str) -> list[str]:
    return [label for label, pattern in PII_PATTERNS.items() if pattern.search(text)]


@dataclass
class InputVerdict:
    allowed: bool
    sanitized: str
    flags: list[str] = field(default_factory=list)


def check_input(question: str) -> InputVerdict:
    text = re.sub(r"\s+", " ", CONTROL_CHARS.sub("", unicodedata.normalize("NFKC", question))).strip()
    flags: list[str] = []
    if len(text) < 3:
        flags.append("too_short")
    if len(text) > MAX_QUESTION_CHARS:
        flags.append("too_long")
    flags += detect_injection(text)
    for label, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            text = pattern.sub(f"[{label}]", text)
            flags.append(f"pii_redacted:{label}")
    return InputVerdict(allowed=not any(not f.startswith("pii_redacted") for f in flags), sanitized=text, flags=flags)


def _amount(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


def check_output(answer: AgentAnswer, ctx: AgentContext) -> list[str]:
    """Devolve a lista de codigos de violacao (vazia = resposta liberada)."""
    out: list[str] = []
    try:
        jsonschema.validate(answer.model_dump(mode="json"), ANSWER_SCHEMA)
    except jsonschema.ValidationError:
        out.append("schema")
    text, plain = answer.answer, fold(answer.answer)

    cited = {c.ref for c in answer.citations}
    used = {int(n) for n in re.findall(r"\[(\d+)\]", text)}
    if used - cited:
        out.append("citation_unknown")
    if (answer.citations and not used) or (not answer.citations and NO_SOURCE not in plain):
        out.append("missing_citation")
    if any(urlparse(c.url).scheme != "https" or not (urlparse(c.url).hostname or "").endswith(ALLOWED_SOURCE_HOST) for c in answer.citations):
        out.append("citation_untrusted_source")

    if detect_pii(text):
        out.append("pii")

    elig = ctx.eligibility
    options = {o.action: o for o in elig.eligible} if elig else {}
    allowed_amounts = {round(v, 2) for o in options.values() for v in (o.cost_brl, o.expected_net_margin_brl)}
    for raw in re.findall(r"R\$\s*(-?\d[\d.]*(?:,\d+)?)", text):
        value = _amount(raw)
        if round(value, 2) not in allowed_amounts:
            out.append("unverified_amount")
            if value > BENEFIT_CAP_BRL:
                out.append("benefit_cap")
            break
    known_numbers = {str(ctx.customer.points_balance)} if ctx.customer else set()
    known_numbers |= {n.replace(".", "") for h in ctx.hits for n in re.findall(r"\d[\d.]*", h.content)}
    if any(n.replace(".", "") not in known_numbers for n in re.findall(r"(\d[\d.]*)\s*(?:pontos|milhas|pts)\b", plain)):
        out.append("unverified_benefit")
    chosen = options.get(answer.proposed_action.action) if answer.proposed_action else None
    if chosen and chosen.cost_brl > BENEFIT_CAP_BRL:
        out.append("benefit_cap")

    mentioned = {name for name, *_ in ACTIONS if fold(name) in plain}
    if mentioned - set(options):
        out.append("ineligible_action")
    p = answer.proposed_action
    if p and (elig is None or p.action != elig.best_action or p.action not in options or p.customer_id != elig.customer_id):
        out.append("ineligible_action")

    if ACTIVATION_CLAIM.search(plain):
        out.append("activation_claim")
    if p and p.requires_approval is not True:
        out.append("approval_required")
    return list(dict.fromkeys(out))


CHECKS = ["schema", "citation", "pii", "benefit_cap", "eligibility", "human_approval"]
