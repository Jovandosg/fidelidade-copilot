"""PSI (Population Stability Index) por feature entre execucoes, com alerta por limiar.

A baseline (bins e proporcoes da execucao anterior) fica em data/analytics/drift_baseline.json, ignorado pelo git.
Cada execucao compara o dado atual com a baseline e depois a substitui.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]
BASELINE = ROOT / "data" / "analytics" / "drift_baseline.json"
PSI_THRESHOLD = 0.2  # convencao: <0.1 estavel, 0.1-0.2 atencao, >=0.2 mudanca relevante
NUMERIC_FEATURES = ("trips_12m", "spend_12m_brl", "avg_ticket_brl", "recency_days", "points_balance", "margin_12m_brl",
                    "disruptions_12m", "complaints_12m", "hvs", "risk_score", "nba_expected_margin_brl")
CATEGORICAL_FEATURES = ("profile", "nba_action")
_EPS = 1e-4


def _numeric_props(values: pd.Series, edges: list[float]) -> list[float]:
    counts = np.histogram(values.dropna().to_numpy(float), bins=[-np.inf, *edges, np.inf])[0]
    return (counts / max(counts.sum(), 1)).tolist()


def snapshot(features: pd.DataFrame) -> dict:
    """Bins (decis) e proporcoes por feature, para servir de baseline na proxima execucao."""
    snap: dict = {}
    for col in NUMERIC_FEATURES:
        edges = np.unique(np.quantile(features[col].dropna().to_numpy(float), np.linspace(0.1, 0.9, 9))).tolist()
        snap[col] = {"type": "numeric", "edges": edges, "props": _numeric_props(features[col], edges)}
    for col in CATEGORICAL_FEATURES:
        snap[col] = {"type": "categorical", "props": features[col].value_counts(normalize=True).to_dict()}
    return snap


def psi(expected: list[float], actual: list[float]) -> float:
    e, a = np.clip(np.array(expected, float), _EPS, None), np.clip(np.array(actual, float), _EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


def compute_drift(features: pd.DataFrame, baseline: dict | None, threshold: float = PSI_THRESHOLD) -> list[dict]:
    """PSI por feature contra a baseline; lista vazia na primeira execucao (sem baseline)."""
    if not baseline:
        return []
    out = []
    for col, base in baseline.items():
        if col not in features.columns:
            continue
        if base["type"] == "numeric":
            expected, actual = base["props"], _numeric_props(features[col], base["edges"])
        else:
            cats = sorted(set(base["props"]) | set(features[col].dropna().unique()))
            cur = features[col].value_counts(normalize=True)
            expected, actual = [base["props"].get(c, 0.0) for c in cats], [float(cur.get(c, 0.0)) for c in cats]
        value = round(psi(expected, actual), 4)
        out.append({"feature": col, "psi": value, "threshold": threshold, "alert": bool(value >= threshold)})
    return out


def read_baseline(path: Path = BASELINE) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def write_baseline(features: pd.DataFrame, path: Path = BASELINE) -> None:
    path.write_text(json.dumps(snapshot(features), ensure_ascii=False), encoding="utf-8")
