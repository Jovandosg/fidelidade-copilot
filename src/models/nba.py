"""Next Best Action por regras, escolhida pela margem esperada liquida.

beneficio esperado = P(churn) x uplift_assumido x margem_12m_em_risco - custo da acao
Custos e uplifts sao PREMISSAS do MVP (sinteticas), nao estimativas de campanhas reais.
Toda acao acima de APPROVAL_COST_BRL exige aprovacao humana.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MONITOR = "Monitorar (sem acao)"
APPROVAL_COST_BRL = 10.0
ACTIONS = [
    # (nome, custo_brl, uplift_retencao_assumido, elegibilidade)
    ("Recuperacao de experiencia (compensacao em pontos + contato proativo)", 25.0, 0.25,
     lambda d: (d.disruptions_12m >= 2) | (d.complaints_12m >= 1)),
    ("Reativacao com bonus de pontos na rota preferida", 15.0, 0.15,
     lambda d: (d.recency_days >= 90) | (d.risk_score >= 50)),
    ("Cortesia de upgrade e reconhecimento de status", 60.0, 0.20,
     lambda d: d.profile.isin(["A", "B"]) & (d.risk_score >= 40)),
    ("Oferta de resgate de pontos", 8.0, 0.08,
     lambda d: d.points_balance >= 15000),
    ("Atendimento premium e reconhecimento", 12.0, 0.05,
     lambda d: d.profile.isin(["A", "B"])),
    ("Oferta personalizada de proxima viagem", 5.0, 0.05,
     lambda d: pd.Series(True, index=d.index)),
]


def compute_nba(df: pd.DataFrame) -> pd.DataFrame:
    """df precisa de: risk_score, profile, margin_12m_brl, disruptions_12m, complaints_12m, points_balance, recency_days."""
    p = df["risk_score"] / 100
    at_stake = df["margin_12m_brl"]
    benefits = np.full((len(df), len(ACTIONS)), -np.inf)
    for j, (_, cost, uplift, eligible) in enumerate(ACTIONS):
        net = p * uplift * at_stake - cost
        benefits[:, j] = np.where(eligible(df).to_numpy(), net.to_numpy(), -np.inf)
    best = benefits.argmax(axis=1)
    best_net = benefits[np.arange(len(df)), best].round(2)
    act = best_net > 0
    names = np.array([a[0] for a in ACTIONS])
    costs = np.array([a[1] for a in ACTIONS])
    out = pd.DataFrame(index=df.index)
    out["nba_action"] = np.where(act, names[best], MONITOR)
    out["nba_expected_margin_brl"] = np.where(act, best_net, 0.0).round(2)
    out["nba_requires_approval"] = act & (costs[best] > APPROVAL_COST_BRL)
    return out
