"""Entradas do model_registry (HVS, Radar de Risco, NBA): metricas, data de treino e hash dos dados."""
from __future__ import annotations

import hashlib

import pandas as pd

MODEL_VERSIONS = {"hvs": "1.0.0", "risk": "1.0.0", "nba": "1.0.0"}
SYNTHETIC_NOTICE = "Metricas calculadas sobre dados sinteticos; nao representam desempenho real."


def data_hash(*frames: pd.DataFrame) -> str:
    """SHA-256 do conteudo (CSV canonico) dos dados de entrada dos modelos."""
    digest = hashlib.sha256()
    for frame in frames:
        digest.update(frame.to_csv(index=False).encode("utf-8"))
    return digest.hexdigest()


def build_registry(model_metrics: dict, trained_at: str, dataset_hash: str) -> list[dict]:
    risk, hvs, nba = dict(model_metrics["risk_radar"]), dict(model_metrics["hvs"]), dict(model_metrics["nba"])
    entries = {
        "risk": {"metrics": {k: risk.pop(k) for k in ("n_train", "n_holdout", "churn_rate_train", "churn_rate_holdout", "holdout",
                                                      "baselines_holdout_roc_auc", "feature_importance")},
                 "params": risk},
        "hvs": {"metrics": {"profile_counts": hvs.pop("profile_counts")}, "params": hvs},
        "nba": {"metrics": {"action_counts": nba.pop("action_counts")}, "params": nba},
    }
    return [{"model_name": name, "model_version": MODEL_VERSIONS[name], "trained_at": trained_at, "data_hash": dataset_hash,
             "metrics": {**e["metrics"], "synthetic_notice": SYNTHETIC_NOTICE}, "params": e["params"]}
            for name, e in entries.items()]
