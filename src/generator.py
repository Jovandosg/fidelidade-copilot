from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

SEED = 20261014
N_CUSTOMERS = 1_200
AS_OF_DATE = pd.Timestamp("2026-09-30")
AIRPORTS = ["VCP", "CGH", "SDU", "CNF", "BSB", "REC", "SSA", "POA", "GYN", "CWB"]
TIERS = ["Azul Fidelidade", "Topázio", "Safira", "Diamante", "Diamante Unique"]
CHANNELS = ["app", "web", "agency"]


def generate_raw(out_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create synthetic source-like tables with a fixed seed and no PII."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    customer_ids = np.array([f"C{i:06d}" for i in range(1, N_CUSTOMERS + 1)])
    tier = rng.choice(TIERS, size=N_CUSTOMERS, p=[0.48, 0.23, 0.16, 0.10, 0.03])
    customers = pd.DataFrame({
        "customer_id": customer_ids,
        "signup_date": pd.to_datetime(rng.integers(pd.Timestamp("2020-01-01").value // 10**9, AS_OF_DATE.value // 10**9, N_CUSTOMERS), unit="s").date,
        "loyalty_tier": tier,
        "home_airport": rng.choice(AIRPORTS, N_CUSTOMERS),
        "preferred_channel": rng.choice(CHANNELS, N_CUSTOMERS, p=[0.55, 0.35, 0.10]),
    }).sort_values("customer_id").reset_index(drop=True)

    tier_factor = pd.Series(tier).map({"Azul Fidelidade": 1.0, "Topázio": 1.15, "Safira": 1.35, "Diamante": 1.65, "Diamante Unique": 2.0}).to_numpy()
    n_events = np.maximum(1, rng.poisson(4.8 * tier_factor))
    rows: list[dict] = []
    tx_no = 1
    for idx, customer_id in enumerate(customer_ids):
        for _ in range(int(n_events[idx])):
            origin = str(customers.iloc[idx].home_airport)
            destination = str(rng.choice([a for a in AIRPORTS if a != origin]))
            flight_date = AS_OF_DATE - pd.Timedelta(int(rng.integers(0, 365)), unit="D")
            base = rng.lognormal(mean=np.log(430 * tier_factor[idx]), sigma=0.38)
            cancelled = bool(rng.random() < 0.055)
            rows.append({
                "transaction_id": f"T{tx_no:08d}",
                "customer_id": customer_id,
                "flight_date": flight_date.date(),
                "origin": origin,
                "destination": destination,
                "amount_brl": round(float(np.clip(base, 120, 4500)), 2),
                "qualifying_points": int(np.round(base * rng.uniform(0.7, 1.3))),
                "cancelled": cancelled,
            })
            tx_no += 1
    transactions = pd.DataFrame(rows).sort_values("transaction_id").reset_index(drop=True)
    customers.to_csv(out / "customers.csv", index=False)
    transactions.to_csv(out / "transactions.csv", index=False)
    return customers, transactions


if __name__ == "__main__":
    generate_raw(Path(__file__).parents[1] / "data" / "raw")
