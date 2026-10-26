from __future__ import annotations

import pandas as pd

from .hvs import HVS_WEIGHTS, PROFILE_THRESHOLDS, compute_hvs
from .nba import ACTIONS, APPROVAL_COST_BRL, compute_nba
from .risk import run_risk_radar


def enrich_with_models(customers: pd.DataFrame, transactions: pd.DataFrame, features: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Acrescenta colunas HVS, Radar de Risco e NBA a customer_features; devolve tambem as metricas."""
    feats = features.set_index("customer_id")
    hvs = compute_hvs(feats)
    risk, risk_metrics = run_risk_radar(customers, transactions)
    merged = feats.join(hvs).join(risk)
    nba = compute_nba(merged)
    out = merged.join(nba).reset_index()
    metrics = {
        "risk_radar": risk_metrics,
        "hvs": {"weights": HVS_WEIGHTS, "profile_thresholds": {label: t for t, label in PROFILE_THRESHOLDS},
                "profile_counts": hvs["profile"].value_counts().sort_index().to_dict()},
        "nba": {"approval_cost_threshold_brl": APPROVAL_COST_BRL,
                "assumptions": [{"action": n, "cost_brl": c, "assumed_uplift": u} for n, c, u, _ in ACTIONS],
                "action_counts": nba["nba_action"].value_counts().to_dict(),
                "note": "Custos e uplifts sao premissas sinteticas; toda acao acima do limite requer aprovacao humana."},
    }
    return out, metrics
