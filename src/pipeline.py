from __future__ import annotations

from pathlib import Path
import pandas as pd
from .generator import generate_raw
from .transform import build_treated, build_analytics, build_route_metrics
from .validation import validate_all

ROOT = Path(__file__).parents[1]


def main() -> None:
    raw = ROOT / "data" / "raw"
    treated = ROOT / "data" / "treated"
    analytics = ROOT / "data" / "analytics"
    customers, transactions = generate_raw(raw)
    customers_t, transactions_t = build_treated(customers, transactions)
    customers_t.to_csv(treated / "customers.csv", index=False)
    transactions_t.to_csv(treated / "transactions.csv", index=False)
    features = build_analytics(customers_t, transactions_t)
    routes = build_route_metrics(transactions_t)
    features.to_csv(analytics / "customer_features.csv", index=False)
    routes.to_csv(analytics / "route_metrics.csv", index=False)
    report = validate_all(customers_t, transactions_t, features, routes, analytics / "quality_report.json")
    print(f"Pipeline concluído: {report['customers']} clientes, {report['transactions']} transações; validação={report['status']}")

if __name__ == "__main__":
    main()
