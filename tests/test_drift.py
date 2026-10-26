"""Registro de modelos e drift (PSI) sem banco."""
import numpy as np
import pandas as pd

from src import drift
from src.drift import CATEGORICAL_FEATURES, NUMERIC_FEATURES, PSI_THRESHOLD, compute_drift, psi, snapshot
from src.pipeline import ROOT, main
from src.registry import MODEL_VERSIONS, SYNTHETIC_NOTICE, data_hash
from src.runs import read_run_report


def _features() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "analytics" / "customer_features.csv")


def test_psi_basics():
    assert psi([0.5, 0.5], [0.5, 0.5]) == 0
    assert psi([0.5, 0.5], [0.9, 0.1]) > PSI_THRESHOLD


def test_no_baseline_means_no_drift_rows():
    assert compute_drift(_features(), None) == []


def test_same_data_has_zero_psi_and_no_alert():
    feats = _features()
    result = compute_drift(feats, snapshot(feats))
    assert {d["feature"] for d in result} == set(NUMERIC_FEATURES) | set(CATEGORICAL_FEATURES)
    assert all(d["psi"] == 0 and not d["alert"] for d in result)


def test_shifted_feature_triggers_alert_only_for_that_feature():
    feats = _features()
    base = snapshot(feats)
    shifted = feats.copy()
    shifted["recency_days"] = shifted["recency_days"] + 400
    shifted["profile"] = "E"
    alerts = {d["feature"] for d in compute_drift(shifted, base) if d["alert"]}
    assert {"recency_days", "profile"} <= alerts
    assert "trips_12m" not in alerts


def test_baseline_threshold_is_configurable():
    feats = _features()
    shifted = feats.assign(hvs=feats["hvs"] * 0.9)
    strict = {d["feature"]: d for d in compute_drift(shifted, snapshot(feats), threshold=0.01)}
    assert strict["hvs"]["alert"] and strict["hvs"]["threshold"] == 0.01


def test_run_records_models_with_hash_metrics_and_notice(tmp_path, monkeypatch):
    monkeypatch.setattr(drift, "BASELINE", tmp_path / "b.json")
    main()
    rep = read_run_report()
    models = {m["model_name"]: m for m in rep["models"]}
    assert set(models) == {"hvs", "risk", "nba"}
    for name, m in models.items():
        assert m["model_version"] == MODEL_VERSIONS[name]
        assert len(m["data_hash"]) == 64 and m["trained_at"] == rep["started_at"]
        assert m["metrics"]["synthetic_notice"] == SYNTHETIC_NOTICE
    assert 0 < models["risk"]["metrics"]["holdout"]["roc_auc"] < 1
    assert len({m["data_hash"] for m in models.values()}) == 1


def test_data_hash_changes_with_data():
    df = pd.DataFrame({"a": [1, 2]})
    assert data_hash(df) == data_hash(df.copy())
    assert data_hash(df) != data_hash(df.assign(a=[1, 3]))
    assert not np.isnan(psi([0.3, 0.7], [0.4, 0.6]))
