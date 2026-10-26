"""Modelos de resposta da API. Linhas de tabela reutilizam src.schemas (espelho das colunas do Postgres)."""
from __future__ import annotations

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
