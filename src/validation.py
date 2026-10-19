from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame, Series

class CustomersSchema(pa.DataFrameModel):
    customer_id: Series[str] = pa.Field(str_matches=r"^C\d{6}$", unique=True, nullable=False)
    signup_date: Series[object] = pa.Field(nullable=False)
    loyalty_tier: Series[str] = pa.Field(isin=["Azul Fidelidade", "Topázio", "Safira", "Diamante", "Diamante Unique"], nullable=False)
    home_airport: Series[str] = pa.Field(str_matches=r"^[A-Z]{3}$", nullable=False)
    preferred_channel: Series[str] = pa.Field(isin=["app", "web", "agency"], nullable=False)

class TransactionsSchema(pa.DataFrameModel):
    transaction_id: Series[str] = pa.Field(str_matches=r"^T\d{8}$", unique=True, nullable=False)
    customer_id: Series[str] = pa.Field(str_matches=r"^C\d{6}$", nullable=False)
    flight_date: Series[object] = pa.Field(nullable=False)
    origin: Series[str] = pa.Field(str_matches=r"^[A-Z]{3}$", nullable=False)
    destination: Series[str] = pa.Field(str_matches=r"^[A-Z]{3}$", nullable=False)
    amount_brl: Series[float] = pa.Field(gt=0, nullable=False)
    qualifying_points: Series[int] = pa.Field(ge=0, nullable=False)
    cancelled: Series[bool] = pa.Field(nullable=False)

class FeaturesSchema(pa.DataFrameModel):
    customer_id: Series[str] = pa.Field(str_matches=r"^C\d{6}$", unique=True, nullable=False)
    trips_12m: Series[int] = pa.Field(ge=0, nullable=False)
    spend_12m_brl: Series[float] = pa.Field(ge=0, nullable=False)
    avg_ticket_brl: Series[float] = pa.Field(ge=0, nullable=False)
    recency_days: Series[int] = pa.Field(ge=0, le=365, nullable=False)
    preferred_route: Series[str] = pa.Field(nullable=False)
    value_score: Series[float] = pa.Field(ge=0, le=100, nullable=False)
    segment: Series[str] = pa.Field(isin=["Estratégico", "Frequente", "Oportunidade", "Em risco"], nullable=False)
    recommended_action: Series[str] = pa.Field(nullable=False)


def validate_all(customers: pd.DataFrame, transactions: pd.DataFrame, features: pd.DataFrame, report_path: str | Path) -> dict:
    CustomersSchema.validate(customers, lazy=True)
    TransactionsSchema.validate(transactions, lazy=True)
    FeaturesSchema.validate(features, lazy=True)
    unknown_customer_ids = set(transactions.customer_id) - set(customers.customer_id)
    if unknown_customer_ids:
        raise ValueError(f"customer_id sem correspondência: {sorted(unknown_customer_ids)[:5]}")
    if (transactions.origin == transactions.destination).any():
        raise ValueError("Há transações com origem igual ao destino")
    if len(customers) != 1200 or len(features) != 1200:
        raise ValueError("O contrato exige exatamente 1.200 clientes")
    report = {
        "status": "passed", "customers": int(len(customers)), "transactions": int(len(transactions)),
        "features": int(len(features)), "null_cells": int(sum(frame.isna().sum().sum() for frame in (customers, transactions, features))),
        "duplicate_customer_ids": int(customers.customer_id.duplicated().sum()),
        "duplicate_transaction_ids": int(transactions.transaction_id.duplicated().sum()),
        "impossible_amounts": int((transactions.amount_brl <= 0).sum()),
        "impossible_routes": int((transactions.origin == transactions.destination).sum()),
    }
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
