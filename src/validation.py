from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from .contracts import build_schema, check_foreign_keys, load_contract


def validate_all(customers: pd.DataFrame, transactions: pd.DataFrame, features: pd.DataFrame, route_metrics: pd.DataFrame, report_path: str | Path) -> dict:
    contract = load_contract()
    frames = {"customers_raw": customers, "transactions_raw": transactions, "customer_features": features, "route_metrics": route_metrics}
    for entity, frame in frames.items():
        build_schema(entity, contract).validate(frame, lazy=True)
    check_foreign_keys(frames, contract)
    if set(features.customer_id) != set(customers.customer_id):
        raise ValueError("customer_features deve ter exatamente um registro por cliente")
    # Regras entre colunas que o contrato declarativo nao expressa.
    inconsistent = int((transactions.disrupted != (transactions.cancelled | (transactions.delay_minutes >= 60))).sum())
    margin_over_amount = int((transactions.margin_brl > transactions.amount_brl).sum())
    if inconsistent or margin_over_amount:
        raise ValueError(f"transactions inconsistentes: disrupted={inconsistent}, margin>amount={margin_over_amount}")
    if int(route_metrics.flights.sum()) != len(transactions):
        raise ValueError("route_metrics.flights deve somar o total de transacoes")
    report = {
        "status": "passed", "customers": int(len(customers)), "transactions": int(len(transactions)),
        "features": int(len(features)), "routes": int(len(route_metrics)),
        "null_cells": int(sum(frame.isna().sum().sum() for frame in (customers, transactions, features, route_metrics))),
        "duplicate_customer_ids": int(customers.customer_id.duplicated().sum()),
        "duplicate_transaction_ids": int(transactions.transaction_id.duplicated().sum()),
        "impossible_amounts": int((transactions.amount_brl <= 0).sum()),
        "impossible_routes": int((transactions.origin == transactions.destination).sum()),
    }
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
