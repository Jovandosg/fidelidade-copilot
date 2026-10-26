"""Contratos tipados do agente: entradas/saidas das ferramentas e a resposta final."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CUSTOMER_ID_PATTERN = r"^C\d{6}$"
SIMULATED_NOTICE = "Simulado: dados sinteticos e premissas de MVP; nenhuma acao e executada sem aprovacao humana."


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- ferramentas ----------
class CustomerQuery(Strict):
    customer_id: str = Field(pattern=CUSTOMER_ID_PATTERN)


class CustomerView(Strict):
    """Somente atributos nao pessoais do cliente sintetico."""
    customer_id: str
    profile: Literal["A", "B", "C", "D", "E"]
    segment: str
    hvs: float
    risk_score: float
    risk_drivers: str
    points_balance: int
    recency_days: int
    nba_action: str
    nba_expected_margin_brl: float
    nba_requires_approval: bool


class EligibilityOption(Strict):
    action: str
    cost_brl: float
    assumed_uplift: float
    expected_net_margin_brl: float


class EligibilityResult(Strict):
    customer_id: str
    eligible: list[EligibilityOption]
    best_action: str
    best_expected_margin_brl: float
    requires_approval: bool
    premises_notice: str = "Custos e uplifts sao premissas sinteticas do MVP, nao estimativas de campanhas reais."


class RuleQuery(Strict):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=3, ge=1, le=5)


class RuleHit(Strict):
    chunk_id: int
    content: str
    section: str
    url: str
    title: str
    version: int
    consulted_at: str
    score: float


class RuleSearchResult(Strict):
    hits: list[RuleHit]


# ---------- resposta ----------
class AskRequest(Strict):
    question: str = Field(min_length=3, max_length=500)


class Citation(Strict):
    ref: int
    url: str
    title: str
    version: int
    consulted_at: str
    section: str
    score: float


class ProposedAction(Strict):
    customer_id: str
    action: str
    expected_margin_brl: float
    requires_approval: Literal[True] = True  # nenhuma proposta do agente dispensa aprovacao humana


class GuardrailReport(Strict):
    status: Literal["passed", "fallback", "blocked"] = "passed"
    input_flags: list[str] = Field(default_factory=list)
    output_violations: list[str] = Field(default_factory=list)  # codigos, nunca trechos do conteudo
    checks: list[str] = Field(default_factory=list)


class AgentAnswer(Strict):
    answer: str
    customer_id: str | None
    proposed_action: ProposedAction | None
    citations: list[Citation]
    tools_used: list[str]
    provider: Literal["rules", "llm"]
    fallback_used: bool
    fallback_reason: Literal["no_credential", "provider_error", "invalid_output", "guardrail_violation"] | None = None
    guardrails: GuardrailReport = Field(default_factory=GuardrailReport)
    simulated: bool = True
    notice: str = SIMULATED_NOTICE
