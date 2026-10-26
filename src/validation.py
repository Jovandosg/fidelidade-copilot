from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from .contracts import build_schema, check_foreign_keys, load_contract, rule_results


def evaluate_rules(customers: pd.DataFrame, transactions: pd.DataFrame, features: pd.DataFrame, route_metrics: pd.DataFrame) -> list[dict]:
    """Todas as regras de qualidade (contrato via pandera + regras entre entidades). Nunca levanta por dado ruim."""
    contract = load_contract()
    frames = {"customers_raw": customers, "transactions_raw": transactions, "customer_features": features, "route_metrics": route_metrics}
    results = [r for entity, frame in frames.items() for r in rule_results(entity, frame, contract)]

    def add(entity: str, rule: str, failed: int) -> None:
        results.append({"entity": entity, "rule": rule, "passed": bool(failed == 0), "failed_rows": int(failed)})

    try:
        check_foreign_keys(frames, contract)
        add("transactions_raw", "fk:customer_id->customers_raw", 0)
    except ValueError:
        add("transactions_raw", "fk:customer_id->customers_raw", len(set(transactions.customer_id) - set(customers.customer_id)))
    add("customer_features", "one_row_per_customer", len(set(features.customer_id) ^ set(customers.customer_id)))
    add("transactions_raw", "disrupted_consistent_with_cancel_or_delay", (transactions.disrupted != (transactions.cancelled | (transactions.delay_minutes >= 60))).sum())
    add("transactions_raw", "margin_not_above_amount", (transactions.margin_brl > transactions.amount_brl).sum())
    add("route_metrics", "flights_sum_equals_transactions", abs(int(route_metrics.flights.sum()) - len(transactions)))
    return results


def validate_all(customers: pd.DataFrame, transactions: pd.DataFrame, features: pd.DataFrame, route_metrics: pd.DataFrame, report_path: str | Path,
                 rules: list[dict] | None = None) -> dict:
    rules = rules if rules is not None else evaluate_rules(customers, transactions, features, route_metrics)
    failed = [r for r in rules if not r["passed"]]
    if failed:
        raise ValueError("regras de qualidade falharam: " + ", ".join(f"{r['entity']}.{r['rule']}({r['failed_rows']})" for r in failed))
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
