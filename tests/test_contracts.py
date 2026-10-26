import pandas as pd
import pandera.pandas as pa
import pytest

from src.contracts import ContractError, build_schema, check_foreign_keys, load_contract


def _customer(**over):
    row = {"customer_id": "C000001", "signup_date": "2024-01-01", "loyalty_tier": "Safira", "home_airport": "VCP", "preferred_channel": "app"}
    row.update(over)
    return pd.DataFrame([row])


def test_contract_loads_and_is_structurally_valid():
    contract = load_contract()
    assert contract["version"]
    assert {"customers_raw", "transactions_raw", "customer_features"} <= set(contract["entities"])


def test_valid_customer_passes():
    build_schema("customers_raw").validate(_customer())


@pytest.mark.parametrize("bad", [
    {"customer_id": "SYN-000001"},
    {"loyalty_tier": "Platina"},
    {"home_airport": "vcp"},
    {"signup_date": "2026-10-01"},
])
def test_invalid_customer_is_rejected(bad):
    with pytest.raises(pa.errors.SchemaError):
        build_schema("customers_raw").validate(_customer(**bad))


def test_features_recency_out_of_range_is_rejected():
    row = {"customer_id": "C000001", "trips_12m": 1, "spend_12m_brl": 10.0, "avg_ticket_brl": 10.0, "recency_days": 366,
           "preferred_route": "VCP-CGH", "value_score": 10.0, "segment": "Frequente", "recommended_action": "x"}
    with pytest.raises(pa.errors.SchemaError):
        build_schema("customer_features").validate(pd.DataFrame([row]))


def test_origin_equal_destination_is_rejected():
    tx = pd.DataFrame([{"transaction_id": "T00000001", "customer_id": "C000001", "flight_date": "2026-01-01", "origin": "VCP",
                        "destination": "VCP", "amount_brl": 100.0, "qualifying_points": 1, "cancelled": False}])
    with pytest.raises(pa.errors.SchemaError):
        build_schema("transactions_raw").validate(tx)


def test_foreign_key_violation_is_rejected():
    tx = pd.DataFrame([{"transaction_id": "T00000001", "customer_id": "C999999"}])
    with pytest.raises(ValueError):
        check_foreign_keys({"customers_raw": _customer(), "transactions_raw": tx})


def test_unsupported_constraint_fails_loudly(tmp_path):
    bad = tmp_path / "c.yml"
    bad.write_text("version: '1'\nentities:\n  e:\n    primary_key: a\n    columns:\n      a: {type: string, nullable: false, constraints: 'banana'}\n", encoding="utf-8")
    with pytest.raises(ContractError):
        build_schema("e", load_contract(bad))
