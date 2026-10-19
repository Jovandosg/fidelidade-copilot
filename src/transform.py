from __future__ import annotations

from pathlib import Path
import pandas as pd

AS_OF_DATE = pd.Timestamp("2026-09-30")
TIER_SCORE = {"Azul Fidelidade": 10, "Topázio": 25, "Safira": 45, "Diamante": 70, "Diamante Unique": 90}


def build_analytics(customers: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    tx = transactions.loc[~transactions["cancelled"]].copy()
    tx["flight_date"] = pd.to_datetime(tx["flight_date"])
    tx["route"] = tx["origin"] + "-" + tx["destination"]
    agg = tx.groupby("customer_id").agg(
        trips_12m=("transaction_id", "count"),
        spend_12m_brl=("amount_brl", "sum"),
        avg_ticket_brl=("amount_brl", "mean"),
        last_flight=("flight_date", "max"),
    )
    route = tx.groupby(["customer_id", "route"]).size().rename("n").reset_index()
    route = route.sort_values(["customer_id", "n", "route"], ascending=[True, False, True]).drop_duplicates("customer_id").set_index("customer_id")
    result = customers.set_index("customer_id").join(agg).join(route[["route"]].rename(columns={"route": "preferred_route"}))
    result[["trips_12m", "spend_12m_brl", "avg_ticket_brl"]] = result[["trips_12m", "spend_12m_brl", "avg_ticket_brl"]].fillna(0)
    result["trips_12m"] = result["trips_12m"].astype(int)
    result["last_flight"] = pd.to_datetime(result["last_flight"])
    result["recency_days"] = (AS_OF_DATE - result["last_flight"]).dt.days.fillna(365).astype(int).clip(0, 365)
    result["preferred_route"] = result["preferred_route"].fillna("N/A-N/A")
    result["tier_score"] = result["loyalty_tier"].map(TIER_SCORE)

    def minmax(s: pd.Series) -> pd.Series:
        return (s - s.min()) / (s.max() - s.min() if s.max() != s.min() else 1)

    result["value_score"] = (0.35 * minmax(result["spend_12m_brl"]) + 0.30 * minmax(result["trips_12m"]) + 0.20 * (1 - result["recency_days"] / 365) + 0.15 * result["tier_score"] / 90) * 100
    result["value_score"] = result["value_score"].round(2)
    result["segment"] = "Oportunidade"
    result.loc[(result["value_score"] >= 70) & (result["recency_days"] <= 90), "segment"] = "Estratégico"
    result.loc[(result["value_score"] >= 45) & (result["recency_days"] <= 180) & (result["segment"] == "Oportunidade"), "segment"] = "Frequente"
    result.loc[(result["value_score"] >= 45) & (result["recency_days"] > 180), "segment"] = "Em risco"
    result["recommended_action"] = result["segment"].map({
        "Estratégico": "Atendimento premium e reconhecimento de status",
        "Frequente": "Bônus de pontos na rota preferida",
        "Oportunidade": "Oferta personalizada de próxima viagem",
        "Em risco": "Campanha de reativação com benefício relevante",
    })
    cols = ["trips_12m", "spend_12m_brl", "avg_ticket_brl", "recency_days", "preferred_route", "value_score", "segment", "recommended_action"]
    return result[cols].reset_index()


def build_treated(customers: pd.DataFrame, transactions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    c = customers.copy()
    c["signup_date"] = pd.to_datetime(c["signup_date"]).dt.date
    t = transactions.copy()
    t["flight_date"] = pd.to_datetime(t["flight_date"]).dt.date
    t["amount_brl"] = t["amount_brl"].round(2)
    return c.sort_values("customer_id"), t.sort_values("transaction_id")
