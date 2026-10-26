from pathlib import Path
import json
import pandas as pd
from src.pipeline import main, ROOT


def test_pipeline_outputs_and_contracts():
    main()
    raw_customers = pd.read_csv(ROOT / "data/raw/customers.csv")
    features = pd.read_csv(ROOT / "data/analytics/customer_features.csv")
    report = json.loads((ROOT / "data/analytics/quality_report.json").read_text())
    assert len(raw_customers) == 1200
    assert len(features) == 1200
    assert features.customer_id.is_unique
    assert report["status"] == "passed"
    assert report["null_cells"] == 0
    assert report["impossible_amounts"] == 0
    assert report["impossible_routes"] == 0


def test_seed_is_reproducible():
    main()
    first = (ROOT / "data/analytics/customer_features.csv").read_bytes()
    raw_first = (ROOT / "data/raw/transactions.csv").read_bytes()
    main()
    second = (ROOT / "data/analytics/customer_features.csv").read_bytes()
    assert first == second
    assert raw_first == (ROOT / "data/raw/transactions.csv").read_bytes()


def test_experience_signals_are_consistent_and_informative():
    main()
    tx = pd.read_csv(ROOT / "data/raw/transactions.csv")
    routes = pd.read_csv(ROOT / "data/analytics/route_metrics.csv")
    features = pd.read_csv(ROOT / "data/analytics/customer_features.csv")
    assert (tx.disrupted == (tx.cancelled | (tx.delay_minutes >= 60))).all()
    assert (tx.loc[tx.cancelled, "margin_brl"] == 0).all()
    assert tx.complaint_flag[tx.disrupted].mean() > 5 * tx.complaint_flag[~tx.disrupted].mean()
    assert routes.flights.sum() == len(tx)
    assert routes.ivr.max() - routes.ivr.min() > 3  # rotas com IVR distinguivel
    assert features.disruptions_12m.sum() == tx.disrupted.sum()
    assert not {"name", "email", "cpf", "phone"} & set(pd.read_csv(ROOT / "data/raw/customers.csv").columns)
