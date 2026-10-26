"""Instrumentacao do pipeline: run_report.json e resultado por regra (sem banco)."""
import json
import re

import pandas as pd
import pytest

from src import pipeline
from src.generator import SEED
from src.contracts import load_contract
from src.pipeline import ROOT, main
from src.runs import RUN_COLUMNS, RUN_REPORT, code_version
from src.validation import evaluate_rules


def _report() -> dict:
    return json.loads(RUN_REPORT.read_text(encoding="utf-8"))


def _frames():
    t = ROOT / "data" / "treated"
    a = ROOT / "data" / "analytics"
    return (pd.read_csv(t / "customers.csv"), pd.read_csv(t / "transactions.csv"),
            pd.read_csv(a / "customer_features.csv"), pd.read_csv(a / "route_metrics.csv"))


def test_run_report_records_run_metadata():
    main()
    rep = _report()
    assert set(RUN_COLUMNS) <= set(rep)
    assert re.fullmatch(r"[0-9a-f-]{36}", rep["run_id"])
    assert rep["status"] == "passed" and rep["error"] is None
    assert rep["seed"] == SEED
    assert rep["contract_version"] == str(load_contract()["version"])
    assert rep["duration_ms"] >= 0 and rep["finished_at"] >= rep["started_at"]
    assert rep["rows_by_entity"] == {"customers_raw": 1200, "transactions_raw": rep["rows_by_entity"]["transactions_raw"],
                                     "customer_features": 1200, "route_metrics": rep["rows_by_entity"]["route_metrics"]}
    assert rep["code_version"] == code_version() or rep["code_version"].endswith("-dirty") or rep["code_version"] == "unknown"


def test_each_run_has_a_new_run_id_but_same_data():
    main()
    first = _report()["run_id"]
    main()
    assert _report()["run_id"] != first


def test_rules_are_listed_per_rule_and_all_pass():
    main()
    rules = _report()["rules"]
    names = {(r["entity"], r["rule"]) for r in rules}
    assert ("customers_raw", "customer_id:unique") in names
    assert ("transactions_raw", "table:destination_ne_origin") in names
    assert ("transactions_raw", "fk:customer_id->customers_raw") in names
    assert ("route_metrics", "flights_sum_equals_transactions") in names
    assert len(names) == len(rules), "regra duplicada"
    assert all(r["passed"] and r["failed_rows"] == 0 for r in rules)


def test_bad_data_points_to_the_exact_rule():
    main()
    customers, transactions, features, routes = _frames()
    transactions.loc[0, "amount_brl"] = -5
    transactions.loc[1, "destination"] = transactions.loc[1, "origin"]
    features.loc[0, "hvs"] = 150
    failed = {(r["entity"], r["rule"]): r["failed_rows"] for r in evaluate_rules(customers, transactions, features, routes) if not r["passed"]}
    assert failed[("transactions_raw", "amount_brl:amount_brl_>")] == 1
    assert failed[("transactions_raw", "table:destination_ne_origin")] == 1
    assert any(entity == "customer_features" and rule.startswith("hvs:") for entity, rule in failed)
    assert not any(entity == "customers_raw" for entity, _ in failed)


def test_failed_run_is_recorded_with_failed_rule(monkeypatch):
    original = pipeline.build_route_metrics

    def corrupt(transactions):
        routes = original(transactions)
        routes.loc[0, "ivr"] = 150
        return routes

    monkeypatch.setattr(pipeline, "build_route_metrics", corrupt)
    try:
        with pytest.raises(ValueError, match="regras de qualidade falharam"):
            main()
        rep = _report()
        assert rep["status"] == "failed" and "regras de qualidade" in rep["error"]
        assert any(r["entity"] == "route_metrics" and not r["passed"] for r in rep["rules"])
    finally:
        monkeypatch.undo()
        main()  # restaura os artefatos validos (data/analytics e run_report)
    assert _report()["status"] == "passed"
