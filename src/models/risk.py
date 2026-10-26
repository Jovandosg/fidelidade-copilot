"""Radar de Risco de churn com rotulo temporal e avaliacao em hold-out temporal.

Definicao: churn = nenhum voo nao cancelado nos 90 dias seguintes ao corte.
Features usam somente dados ate o corte (sem vazamento de futuro).
- treino: corte 2026-03-31 (rotulo observado em 04-01..06-29)
- hold-out: corte 2026-06-30 (rotulo observado em 07-01..09-28), nunca visto no treino
O modelo final (usado no score) e reajustado em treino+hold-out e pontua o corte 2026-09-30.
Dados sinteticos: as metricas descrevem o gerador, NAO sao previsao validada.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

SEED = 20261014
LABEL_DAYS = 90
LOOKBACK_DAYS = 180
TRAIN_CUTOFF = pd.Timestamp("2026-03-31")
HOLDOUT_CUTOFF = pd.Timestamp("2026-06-30")
SCORE_CUTOFF = pd.Timestamp("2026-09-30")
TIER_ORDER = {"Azul Fidelidade": 0, "Topázio": 1, "Safira": 2, "Diamante": 3, "Diamante Unique": 4}
CABIN_ORDER = {"economy": 0, "premium": 1, "business": 2}
FEATURE_LABELS = {
    "trips_90d": "poucos voos nos ultimos 90 dias",
    "trips_180d": "baixa frequencia em 180 dias",
    "recency_days": "muito tempo sem voar",
    "spend_180d": "gasto recente baixo",
    "margin_180d": "margem recente baixa",
    "disruptions_90d": "disrupcoes recentes (90 dias)",
    "disruptions_180d": "disrupcoes em 180 dias",
    "complaints_180d": "reclamacoes recentes",
    "avg_delay_180d": "atraso medio elevado",
    "tier_idx": "nivel de fidelidade",
    "points_balance": "saldo de pontos",
    "is_corporate": "perfil corporativo",
    "cabin_idx": "cabine predominante",
}
FEATURES = list(FEATURE_LABELS)


def _prepare(transactions: pd.DataFrame) -> pd.DataFrame:
    tx = transactions.copy()
    tx["flight_date"] = pd.to_datetime(tx["flight_date"])
    return tx


def snapshot_features(customers: pd.DataFrame, tx: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Features de um cliente no corte, usando apenas transacoes com flight_date <= cutoff."""
    past = tx[(tx["flight_date"] <= cutoff) & (tx["flight_date"] > cutoff - pd.Timedelta(days=LOOKBACK_DAYS))]
    flown = past[~past["cancelled"]]
    recent = flown[flown["flight_date"] > cutoff - pd.Timedelta(days=90)]
    g = flown.groupby("customer_id")
    base = customers.set_index("customer_id")
    out = pd.DataFrame(index=base.index)
    out["trips_90d"] = recent.groupby("customer_id").size()
    out["trips_180d"] = g.size()
    out["recency_days"] = (cutoff - g["flight_date"].max()).dt.days
    out["spend_180d"] = g["amount_brl"].sum()
    out["margin_180d"] = g["margin_brl"].sum()
    out["disruptions_90d"] = past[past["flight_date"] > cutoff - pd.Timedelta(days=90)].groupby("customer_id")["disrupted"].sum()
    out["disruptions_180d"] = past.groupby("customer_id")["disrupted"].sum()
    out["complaints_180d"] = past.groupby("customer_id")["complaint_flag"].sum()
    out["avg_delay_180d"] = past.groupby("customer_id")["delay_minutes"].mean()
    out["recency_days"] = out["recency_days"].fillna(LOOKBACK_DAYS)
    out = out.fillna(0)
    out["tier_idx"] = base["loyalty_tier"].map(TIER_ORDER)
    out["points_balance"] = base["points_balance"]
    out["is_corporate"] = base["is_corporate"].astype(int)
    out["cabin_idx"] = base["primary_cabin"].map(CABIN_ORDER)
    out["_active"] = out["trips_180d"] > 0
    return out


def churn_label(tx: pd.DataFrame, customer_ids: pd.Index, cutoff: pd.Timestamp) -> pd.Series:
    future = tx[(tx["flight_date"] > cutoff) & (tx["flight_date"] <= cutoff + pd.Timedelta(days=LABEL_DAYS)) & (~tx["cancelled"])]
    flew = set(future["customer_id"])
    return pd.Series([cid not in flew for cid in customer_ids], index=customer_ids).astype(int)


def _dataset(customers: pd.DataFrame, tx: pd.DataFrame, cutoff: pd.Timestamp) -> tuple[pd.DataFrame, pd.Series]:
    snap = snapshot_features(customers, tx, cutoff)
    snap = snap[snap["_active"]]  # populacao em risco: ativos no ultimo semestre
    return snap[FEATURES], churn_label(tx, snap.index, cutoff)


def _model() -> GradientBoostingClassifier:
    return GradientBoostingClassifier(n_estimators=80, max_depth=2, learning_rate=0.05, subsample=0.8, min_samples_leaf=30, random_state=SEED)


def _driver_text(model: GradientBoostingClassifier, X: pd.DataFrame, reference: pd.DataFrame) -> pd.Series:
    """Top-3 fatores que elevam o risco: efeito de trocar cada feature pela mediana de referencia."""
    base = model.predict_proba(X)[:, 1]
    deltas = {}
    for col in FEATURES:
        alt = X.copy()
        alt[col] = reference[col].median()
        deltas[col] = base - model.predict_proba(alt)[:, 1]
    delta = pd.DataFrame(deltas, index=X.index)
    texts = []
    for _, row in delta.iterrows():
        top = row[row > 0.01].sort_values(ascending=False, kind="stable").head(3)
        texts.append("; ".join(FEATURE_LABELS[c] for c in top.index) or "sem fator dominante")
    return pd.Series(texts, index=X.index)


def run_risk_radar(customers: pd.DataFrame, transactions: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    tx = _prepare(transactions)
    X_tr, y_tr = _dataset(customers, tx, TRAIN_CUTOFF)
    X_ho, y_ho = _dataset(customers, tx, HOLDOUT_CUTOFF)
    model = _model().fit(X_tr, y_tr)
    p_ho = model.predict_proba(X_ho)[:, 1]
    metrics = {
        "split": {"train_cutoff": str(TRAIN_CUTOFF.date()), "holdout_cutoff": str(HOLDOUT_CUTOFF.date()),
                  "label": f"sem voo nao cancelado em {LABEL_DAYS} dias", "lookback_days": LOOKBACK_DAYS},
        "n_train": int(len(y_tr)), "n_holdout": int(len(y_ho)),
        "churn_rate_train": round(float(y_tr.mean()), 4), "churn_rate_holdout": round(float(y_ho.mean()), 4),
        "holdout": {
            "roc_auc": round(float(roc_auc_score(y_ho, p_ho)), 4),
            "pr_auc": round(float(average_precision_score(y_ho, p_ho)), 4),
            "brier": round(float(brier_score_loss(y_ho, p_ho)), 4),
            "brier_baseline_constant": round(float(brier_score_loss(y_ho, np.full(len(y_ho), y_tr.mean()))), 4),
        },
        "baselines_holdout_roc_auc": {
            "recency_days": round(float(roc_auc_score(y_ho, X_ho["recency_days"])), 4),
            "trips_180d_inverse": round(float(roc_auc_score(y_ho, -X_ho["trips_180d"])), 4),
        },
        "feature_importance": {k: round(float(v), 4) for k, v in sorted(zip(FEATURES, model.feature_importances_), key=lambda kv: -kv[1])},
        "disclaimer": "Dados sinteticos: metricas descrevem o gerador e nao constituem previsao validada.",
    }
    ref = pd.concat([X_tr, X_ho])
    final = _model().fit(ref, pd.concat([y_tr, y_ho]))
    X_now = snapshot_features(customers, tx, SCORE_CUTOFF)[FEATURES]
    out = pd.DataFrame(index=X_now.index)
    out["risk_score"] = (final.predict_proba(X_now)[:, 1] * 100).round(2)
    out["risk_drivers"] = _driver_text(final, X_now, ref)
    return out, metrics
