"""Modelos de resposta da API. Linhas de tabela reutilizam src.schemas (espelho das colunas do Postgres)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..schemas import CustomerFeature, RouteMetric

SYNTHETIC_NOTICE = (
    "Dados sinteticos gerados para o desafio; nao representam clientes reais. "
    "Scores de risco sao estimativas de um modelo simples, sem previsao validada."
)


class Page(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class CustomerPage(Page):
    items: list[CustomerFeature]


class RoutePage(Page):
    items: list[RouteMetric]


class DistributionItem(BaseModel):
    key: str
    customers: int = Field(ge=0)


class Kpis(BaseModel):
    synthetic_data: bool = True
    notice: str = SYNTHETIC_NOTICE
    total_customers: int
    avg_hvs: float
    avg_risk_score: float
    risk_threshold: float
    high_risk_customers: int
    spend_12m_at_risk_brl: float
    nba_expected_margin_brl: float
    nba_pending_approval: int
    avg_route_ivr: float
    profiles: list[DistributionItem]
    segments: list[DistributionItem]


class NbaItem(BaseModel):
    customer_id: str
    profile: str
    segment: str
    hvs: float
    risk_score: float
    nba_action: str
    nba_expected_margin_brl: float
    nba_requires_approval: bool


class NbaSummary(BaseModel):
    nba_action: str
    customers: int
    expected_margin_brl: float
    pending_approval: int


class NbaPage(Page):
    human_approval_notice: str = (
        "Acoes com custo acima do limite exigem aprovacao humana antes de qualquer contato com o cliente."
    )
    summary: list[NbaSummary]
    items: list[NbaItem]


class PipelineRunOut(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    status: str
    code_version: str
    seed: int
    contract_version: str
    rows_by_entity: dict[str, int]
    error: str | None


class QualityRuleOut(BaseModel):
    entity: str
    rule: str
    passed: bool
    failed_rows: int


class QualityOut(BaseModel):
    run_id: str | None
    total_rules: int
    failed_rules: int
    results: list[QualityRuleOut]


class ModelOut(BaseModel):
    model_name: str
    model_version: str
    run_id: str | None
    trained_at: datetime
    data_hash: str
    metrics: dict
    params: dict
    synthetic_notice: str


class DriftOut(BaseModel):
    feature: str
    psi: float
    threshold: float
    alert: bool


class DriftReport(BaseModel):
    run_id: str | None
    computed_at: datetime | None
    alerts: int
    items: list[DriftOut]


class AuditEntry(BaseModel):
    id: int
    occurred_at: datetime
    actor: str
    actor_role: str
    action: str
    entity: str
    entity_id: str
    before: dict | None
    after: dict | None
    request_id: str | None


class AuditPage(Page):
    items: list[AuditEntry]


class ApprovalRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=5, max_length=500, description="Justificativa; nao inclua dados pessoais")


class ApprovalResult(BaseModel):
    audit_id: int
    occurred_at: datetime
    customer_id: str
    decision: Literal["approve", "reject"]
    before: dict
    after: dict


class ApprovalStatus(BaseModel):
    customer_id: str
    decision: Literal["approve", "reject"]
    actor: str
    occurred_at: datetime
