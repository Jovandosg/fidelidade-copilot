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
CABINS = ["economy", "premium", "business"]
CABIN_MARGIN_RATE = {"economy": 0.12, "premium": 0.17, "business": 0.23}
DISRUPTION_DELAY_MIN = 60  # atraso a partir do qual o voo conta como disrupcao


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

    # Sinais adicionais (sorteios apos os originais, para manter a seed estavel).
    tier_idx = pd.Series(tier).map({t: i for i, t in enumerate(TIERS)}).to_numpy()
    tier_factor = pd.Series(tier).map({"Azul Fidelidade": 1.0, "Topázio": 1.15, "Safira": 1.35, "Diamante": 1.65, "Diamante Unique": 2.0}).to_numpy()
    customers["points_balance"] = np.round(rng.lognormal(np.log(6000 * tier_factor), 0.7)).astype(int)
    customers["is_corporate"] = rng.random(N_CUSTOMERS) < (0.05 + 0.05 * tier_idx)
    cabin_p = np.array([[0.90, 0.09, 0.01], [0.82, 0.15, 0.03], [0.70, 0.22, 0.08], [0.50, 0.30, 0.20], [0.30, 0.30, 0.40]])[tier_idx]
    customers["primary_cabin"] = [CABINS[int(rng.choice(3, p=p))] for p in cabin_p]
    # Irregularidade por aeroporto: rotas herdam o risco medio dos dois extremos.
    airport_risk = dict(zip(AIRPORTS, rng.uniform(0.02, 0.14, len(AIRPORTS))))
    cabin_by_customer = dict(zip(customers.customer_id, customers.primary_cabin))
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
            p_disrupt = (airport_risk[origin] + airport_risk[destination]) / 2
            if cancelled:
                delay = 0
            elif rng.random() < p_disrupt:
                delay = int(np.clip(DISRUPTION_DELAY_MIN + rng.exponential(80), DISRUPTION_DELAY_MIN, 600))
            else:
                delay = int(np.clip(rng.exponential(12), 0, DISRUPTION_DELAY_MIN - 1))
            disrupted = cancelled or delay >= DISRUPTION_DELAY_MIN
            complaint = bool(rng.random() < (0.25 if disrupted else 0.01))
            amount = round(float(np.clip(base, 120, 4500)), 2)
            margin = 0.0 if cancelled else amount * CABIN_MARGIN_RATE[cabin_by_customer[customer_id]] * rng.uniform(0.8, 1.2) * (0.7 if disrupted else 1.0)
            rows.append({
                "transaction_id": f"T{tx_no:08d}",
                "customer_id": customer_id,
                "flight_date": flight_date.date(),
                "origin": origin,
                "destination": destination,
                "amount_brl": amount,
                "qualifying_points": int(np.round(base * rng.uniform(0.7, 1.3))),
                "cancelled": cancelled,
                "margin_brl": round(float(margin), 2),
                "delay_minutes": delay,
                "disrupted": bool(disrupted),
                "complaint_flag": complaint,
            })
            tx_no += 1
    transactions = pd.DataFrame(rows).sort_values("transaction_id").reset_index(drop=True)
    customers.to_csv(out / "customers.csv", index=False)
    transactions.to_csv(out / "transactions.csv", index=False)
    return customers, transactions


if __name__ == "__main__":
    generate_raw(Path(__file__).parents[1] / "data" / "raw")
