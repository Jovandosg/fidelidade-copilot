"""High-Value Score (HVS) explicavel: todos os componentes ficam visiveis nas colunas de saida.

Formulacao aditiva (auditavel linha a linha), inspirada em CLV x estabilidade x margem - custo de servir:
    hvs = clip(w_clv*clv + w_margin*margin + w_stability*stability - w_cost*cost_to_serve, 0, 100)
Todos os componentes estao em 0-100. Pesos sao premissas do MVP, nao parametros estimados.
"""
from __future__ import annotations

import pandas as pd

HVS_WEIGHTS = {"clv": 0.40, "margin": 0.30, "stability": 0.30, "cost_to_serve": 0.20}
PROFILE_THRESHOLDS = [(75, "A"), (60, "B"), (45, "C"), (30, "D")]  # abaixo de 30 -> E


def _pct(s: pd.Series) -> pd.Series:
    return s.rank(pct=True) * 100


def assign_profile(hvs: pd.Series) -> pd.Series:
    out = pd.Series("E", index=hvs.index)
    for threshold, label in reversed(PROFILE_THRESHOLDS):
        out[hvs >= threshold] = label
    return out


def compute_hvs(features: pd.DataFrame) -> pd.DataFrame:
    """Recebe customer_features (com sinais da v1.1.0) e devolve as colunas hvs_*, hvs e profile."""
    out = pd.DataFrame(index=features.index)
    out["hvs_clv"] = 0.7 * _pct(features["spend_12m_brl"]) + 0.3 * _pct(features["trips_12m"])
    out["hvs_margin"] = _pct(features["margin_12m_brl"])
    recency_score = 100 * (1 - features["recency_days"] / 365)
    regularity = (features["trips_12m"] / 8).clip(upper=1) * 100
    out["hvs_stability"] = 0.6 * recency_score + 0.4 * regularity
    friction = 0.6 * (features["disruptions_12m"] / 4).clip(upper=1) + 0.4 * (features["complaints_12m"] / 2).clip(upper=1)
    out["hvs_cost_to_serve"] = 100 * friction
    w = HVS_WEIGHTS
    out["hvs"] = (w["clv"] * out["hvs_clv"] + w["margin"] * out["hvs_margin"]
                  + w["stability"] * out["hvs_stability"] - w["cost_to_serve"] * out["hvs_cost_to_serve"]).clip(0, 100)
    out["profile"] = assign_profile(out["hvs"])
    for col in ("hvs_clv", "hvs_margin", "hvs_stability", "hvs_cost_to_serve", "hvs"):
        out[col] = out[col].round(2)
    return out
