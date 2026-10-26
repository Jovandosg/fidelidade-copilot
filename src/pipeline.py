from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from .generator import SEED, generate_raw
from .models import enrich_with_models
from .runs import PipelineRun, write_run_report
from .contracts import load_contract
from .transform import build_treated, build_analytics, build_route_metrics
from .validation import evaluate_rules, validate_all

ROOT = Path(__file__).parents[1]


def main() -> dict:
    run = PipelineRun(SEED, str(load_contract()["version"]))
    try:
        report = _run(run)
    except Exception as exc:
        write_run_report(run.finish("failed", f"{type(exc).__name__}: {exc}"[:2000]), ROOT / "data" / "analytics" / "run_report.json")
        raise
    write_run_report(run.finish("passed"), ROOT / "data" / "analytics" / "run_report.json")
    return report


def _run(run: PipelineRun) -> dict:
    raw = ROOT / "data" / "raw"
    treated = ROOT / "data" / "treated"
    analytics = ROOT / "data" / "analytics"
    customers, transactions = generate_raw(raw)
    customers_t, transactions_t = build_treated(customers, transactions)
    customers_t.to_csv(treated / "customers.csv", index=False)
    transactions_t.to_csv(treated / "transactions.csv", index=False)
    features = build_analytics(customers_t, transactions_t)
    features, model_metrics = enrich_with_models(customers_t, transactions_t, features)
    routes = build_route_metrics(transactions_t)
    features.to_csv(analytics / "customer_features.csv", index=False)
    routes.to_csv(analytics / "route_metrics.csv", index=False)
    (analytics / "model_metrics.json").write_text(json.dumps(model_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    run.rows_by_entity = {"customers_raw": len(customers_t), "transactions_raw": len(transactions_t),
                          "customer_features": len(features), "route_metrics": len(routes)}
    run.rules = evaluate_rules(customers_t, transactions_t, features, routes)
    report = validate_all(customers_t, transactions_t, features, routes, analytics / "quality_report.json", rules=run.rules)
    print(f"Pipeline concluído: {report['customers']} clientes, {report['transactions']} transações; validação={report['status']}")

    return report


if __name__ == "__main__":
    main()
