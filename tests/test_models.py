import json

import pandas as pd
import pytest

from src.models.hvs import HVS_WEIGHTS, compute_hvs
from src.models.nba import ACTIONS, MONITOR, compute_nba
from src.models.risk import HOLDOUT_CUTOFF, TRAIN_CUTOFF, _prepare, snapshot_features
from src.pipeline import ROOT, main


@pytest.fixture(scope="module")
def outputs():
    main()
    return {
        "features": pd.read_csv(ROOT / "data/analytics/customer_features.csv"),
        "metrics": json.loads((ROOT / "data/analytics/model_metrics.json").read_text(encoding="utf-8")),
        "tx": pd.read_csv(ROOT / "data/treated/transactions.csv"),
        "customers": pd.read_csv(ROOT / "data/treated/customers.csv"),
    }


def _base(**over):
    row = {"spend_12m_brl": 1000.0, "trips_12m": 4, "margin_12m_brl": 120.0, "recency_days": 30, "disruptions_12m": 0, "complaints_12m": 0}
    row.update(over)
    return row


def test_hvs_components_visible_bounded_and_consistent(outputs):
    f = outputs["features"]
    comps = ["hvs_clv", "hvs_margin", "hvs_stability", "hvs_cost_to_serve"]
    assert f[comps + ["hvs"]].ge(0).all().all() and f[comps + ["hvs"]].le(100).all().all()
    w = HVS_WEIGHTS
    expected = (w["clv"] * f.hvs_clv + w["margin"] * f.hvs_margin + w["stability"] * f.hvs_stability - w["cost_to_serve"] * f.hvs_cost_to_serve).clip(0, 100)
    assert (expected - f.hvs).abs().max() < 0.05  # explicavel: hvs reconstruido pelos componentes
    assert set(f.profile) <= set("ABCDE")


def test_hvs_penalises_friction_and_rewards_margin():
    df = pd.DataFrame([_base(), _base(disruptions_12m=4, complaints_12m=2), _base(margin_12m_brl=500.0)] + [_base(spend_12m_brl=s, margin_12m_brl=s * 0.1, trips_12m=2) for s in (100, 300, 2000)])
    out = compute_hvs(df)
    assert out.hvs.iloc[1] < out.hvs.iloc[0] < out.hvs.iloc[2]


def test_risk_features_do_not_leak_future(outputs):
    tx = _prepare(outputs["tx"])
    cust = outputs["customers"]
    before = snapshot_features(cust, tx, TRAIN_CUTOFF)
    mutated = tx.copy()
    future = mutated["flight_date"] > TRAIN_CUTOFF
    mutated.loc[future, ["amount_brl", "margin_brl", "delay_minutes"]] = 9999
    mutated.loc[future, ["cancelled", "disrupted", "complaint_flag"]] = True
    pd.testing.assert_frame_equal(before, snapshot_features(cust, mutated, TRAIN_CUTOFF))


def test_risk_split_is_temporal_and_metrics_saved(outputs):
    m = outputs["metrics"]["risk_radar"]
    assert TRAIN_CUTOFF < HOLDOUT_CUTOFF and m["split"]["train_cutoff"] < m["split"]["holdout_cutoff"]
    assert m["n_train"] > 500 and m["n_holdout"] > 500
    assert 0.5 < m["holdout"]["roc_auc"] <= 1 and "disclaimer" in m
    f = outputs["features"]
    assert f.risk_score.between(0, 100).all() and (f.risk_drivers.str.len() > 0).all()


def test_nba_net_margin_rules_and_approval():
    df = pd.DataFrame([
        {"risk_score": 80.0, "profile": "A", "margin_12m_brl": 2000.0, "disruptions_12m": 3, "complaints_12m": 1, "points_balance": 20000, "recency_days": 120},
        {"risk_score": 5.0, "profile": "E", "margin_12m_brl": 20.0, "disruptions_12m": 0, "complaints_12m": 0, "points_balance": 0, "recency_days": 10},
        {"risk_score": 30.0, "profile": "C", "margin_12m_brl": 400.0, "disruptions_12m": 0, "complaints_12m": 0, "points_balance": 20000, "recency_days": 10},
    ])
    out = compute_nba(df)
    assert out.nba_action.iloc[1] == MONITOR and out.nba_expected_margin_brl.iloc[1] == 0 and not out.nba_requires_approval.iloc[1]
    assert out.nba_expected_margin_brl.iloc[0] > out.nba_expected_margin_brl.iloc[2] > 0
    assert out.nba_requires_approval.iloc[0]
    assert (out.nba_expected_margin_brl >= 0).all()


def test_nba_outputs_in_pipeline(outputs):
    f = outputs["features"]
    valid = {a[0] for a in ACTIONS} | {MONITOR}
    assert set(f.nba_action) <= valid
    assert (f.loc[f.nba_action == MONITOR, "nba_expected_margin_brl"] == 0).all()
    assert (f.loc[f.nba_action != MONITOR, "nba_expected_margin_brl"] > 0).all()
