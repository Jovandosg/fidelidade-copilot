"""Schemas Pydantic que espelham 1:1 as colunas das tabelas analytics.* (base da API da Task5)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CustomerFeature(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    customer_id: str
    trips_12m: int = Field(ge=0)
    spend_12m_brl: float = Field(ge=0)
    avg_ticket_brl: float = Field(ge=0)
    recency_days: int = Field(ge=0, le=365)
    preferred_route: str
    value_score: float = Field(ge=0, le=100)
    segment: str
    recommended_action: str
    points_balance: int = Field(ge=0)
    margin_12m_brl: float = Field(ge=0)
    disruptions_12m: int = Field(ge=0)
    complaints_12m: int = Field(ge=0)
    hvs_clv: float = Field(ge=0, le=100)
    hvs_margin: float = Field(ge=0, le=100)
    hvs_stability: float = Field(ge=0, le=100)
    hvs_cost_to_serve: float = Field(ge=0, le=100)
    hvs: float = Field(ge=0, le=100)
    profile: str = Field(pattern="^[A-E]$")
    risk_score: float = Field(ge=0, le=100)
    risk_drivers: str
    nba_action: str
    nba_expected_margin_brl: float = Field(ge=0)
    nba_requires_approval: bool


class RouteMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    route: str = Field(pattern="^[A-Z]{3}-[A-Z]{3}$")
    flights: int = Field(ge=1)
    disrupted_flights: int = Field(ge=0)
    avg_delay_minutes: float = Field(ge=0)
    complaints: int = Field(ge=0)
    revenue_brl: float = Field(ge=0)
    ivr: float = Field(ge=0, le=100)


MODELS = {"customer_features": CustomerFeature, "route_metrics": RouteMetric}
