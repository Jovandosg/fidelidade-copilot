import pandas as pd
import pandera.pandas as pa
import pytest

from src.contracts import ContractError, build_schema, check_foreign_keys, load_contract


def _customer(**over):
    row = {"customer_id": "C000001", "signup_date": "2024-01-01", "loyalty_tier": "Safira", "home_airport": "VCP", "preferred_channel": "app",
           "points_balance": 1000, "is_corporate": False, "primary_cabin": "economy"}
    row.update(over)
    return pd.DataFrame([row])


def _tx(**over):
    row = {"transaction_id": "T00000001", "customer_id": "C000001", "flight_date": "2026-01-01", "origin": "VCP", "destination": "CGH",
           "amount_brl": 100.0, "qualifying_points": 1, "cancelled": False, "margin_brl": 12.0, "delay_minutes": 0,
           "disrupted": False, "complaint_flag": False}
    row.update(over)
    return pd.DataFrame([row])


def _features(**over):
    row = {"customer_id": "C000001", "trips_12m": 1, "spend_12m_brl": 10.0, "avg_ticket_brl": 10.0, "recency_days": 10,
           "preferred_route": "VCP-CGH", "value_score": 10.0, "segment": "Frequente", "recommended_action": "x",
           "points_balance": 1000, "margin_12m_brl": 1.0, "disruptions_12m": 0, "complaints_12m": 0,
           "hvs_clv": 50.0, "hvs_margin": 50.0, "hvs_stability": 50.0, "hvs_cost_to_serve": 0.0, "hvs": 45.0, "profile": "C",
           "risk_score": 30.0, "risk_drivers": "sem fator dominante", "nba_action": "Monitorar (sem acao)",
           "nba_expected_margin_brl": 0.0, "nba_requires_approval": False}
    row.update(over)
    return pd.DataFrame([row])


def test_contract_loads_and_is_structurally_valid():
    contract = load_contract()
    assert contract["version"] == contract["changelog"][0]["version"]
    assert contract["synthetic"] is True
    assert {"customers_raw", "transactions_raw", "customer_features", "route_metrics"} <= set(contract["entities"])


def test_valid_rows_pass():
    build_schema("customers_raw").validate(_customer())
    build_schema("transactions_raw").validate(_tx())
    build_schema("customer_features").validate(_features())


@pytest.mark.parametrize("bad", [
    {"customer_id": "SYN-000001"},
    {"loyalty_tier": "Platina"},
    {"home_airport": "vcp"},
    {"signup_date": "2026-10-01"},
    {"primary_cabin": "first"},
    {"points_balance": -1},
])
def test_invalid_customer_is_rejected(bad):
    with pytest.raises(pa.errors.SchemaError):
        build_schema("customers_raw").validate(_customer(**bad))


@pytest.mark.parametrize("bad", [{"delay_minutes": 601}, {"delay_minutes": -1}, {"margin_brl": -5.0}, {"destination": "VCP"}])
def test_invalid_transaction_is_rejected(bad):
    with pytest.raises(pa.errors.SchemaError):
        build_schema("transactions_raw").validate(_tx(**bad))


@pytest.mark.parametrize("bad", [{"recency_days": 366}, {"disruptions_12m": -1}, {"margin_12m_brl": -1.0},
                                 {"hvs": 100.5}, {"risk_score": -1.0}, {"profile": "F"}, {"nba_expected_margin_brl": -1.0}])
def test_invalid_features_are_rejected(bad):
    with pytest.raises(pa.errors.SchemaError):
        build_schema("customer_features").validate(_features(**bad))


def test_route_metrics_ivr_range_and_route_format():
    ok = pd.DataFrame([{"route": "VCP-CGH", "flights": 10, "disrupted_flights": 2, "avg_delay_minutes": 5.0, "complaints": 1, "revenue_brl": 100.0, "ivr": 20.0}])
    build_schema("route_metrics").validate(ok)
    for bad in ({"ivr": 101.0}, {"route": "vcp-cgh"}):
        with pytest.raises(pa.errors.SchemaError):
            build_schema("route_metrics").validate(ok.assign(**bad))


def test_foreign_key_violation_is_rejected():
    tx = _tx(customer_id="C999999")[["transaction_id", "customer_id"]]
    with pytest.raises(ValueError):
        check_foreign_keys({"customers_raw": _customer(), "transactions_raw": tx})


def test_unsupported_constraint_fails_loudly(tmp_path):
    bad = tmp_path / "c.yml"
    bad.write_text("version: '1'\nentities:\n  e:\n    primary_key: a\n    columns:\n      a: {type: string, nullable: false, constraints: 'banana'}\n", encoding="utf-8")
    with pytest.raises(ContractError):
        build_schema("e", load_contract(bad))
