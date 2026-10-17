"""Gera uma base sintética e materializa analytics para o MVP Azul CRM."""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).parent
RAW = ROOT / "data/raw"
TREATED = ROOT / "data/treated"
ANALYTICS = ROOT / "data/analytics"
SEED = 42


def build(n: int = 1200) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    customer_id = [f"SYN-{i:06d}" for i in range(1, n + 1)]
    frequency = rng.poisson(7, n) + 1
    recency = rng.integers(5, 365, n)
    revenue = np.round(rng.lognormal(7.5, 0.7, n), 2)
    margin = np.round(revenue * rng.uniform(0.18, 0.42, n), 2)
    routes = rng.choice(["CNF-VCP", "REC-GRU", "BSB-SSA", "VCP-LIS", "POA-CNF"], n)
    engagement = rng.uniform(0, 1, n)
    growth = rng.uniform(0, 1, n)
    complaints = rng.poisson(1.2, n)
    corporate = rng.binomial(1, 0.32, n)
    experience_sentiment = np.clip(rng.normal(0.62 - complaints * 0.08, 0.22, n), 0, 1)
    clv = np.round(margin * (1 + growth) * (1 + frequency / 12), 2)
    churn_signal = (recency / 365) + complaints * 0.08 - frequency / 40 - experience_sentiment * 0.35
    churn = (churn_signal > np.quantile(churn_signal, 0.65)).astype(int)
    df = pd.DataFrame({
        "customer_id": customer_id, "frequency_12m": frequency, "recency_days": recency,
        "revenue": revenue, "estimated_margin": margin, "clv": clv, "route": routes,
        "engagement": engagement, "growth_potential": growth, "complaints": complaints,
        "corporate": corporate, "experience_sentiment": experience_sentiment,
        "churn_label": churn,
    })
    for c in ["revenue", "frequency_12m", "clv", "growth_potential", "engagement"]:
        lo, hi = df[c].min(), df[c].max()
        df[c + "_norm"] = (df[c] - lo) / (hi - lo + 1e-9)
    df["high_value_score"] = np.round(100 * (
        .25 * (df["estimated_margin"] / (df["estimated_margin"].max() + 1e-9)) +
        .20 * (.6 * df["frequency_12m_norm"] + .4 * (1 - df["recency_days"] / 365)) +
        .20 * (df["clv"] / (df["clv"].max() + 1e-9)) +
        .15 * df["growth_potential_norm"] +
        .10 * df["engagement_norm"] +
        .10 * df["experience_sentiment"]
    )).clip(0, 100)
    model = Pipeline([("scale", StandardScaler()), ("lr", LogisticRegression(random_state=SEED))])
    features = ["recency_days", "frequency_12m", "complaints", "experience_sentiment", "growth_potential"]
    model.fit(df[features], df["churn_label"])
    df["churn_risk"] = model.predict_proba(df[features])[:, 1].round(4)
    q_score = df.high_value_score.quantile(.68)
    q_risk = df.churn_risk.quantile(.62)
    q_growth = df.growth_potential.quantile(.68)
    df["segment"] = np.select([
        (df.high_value_score >= q_score) & (df.churn_risk < q_risk),
        (df.high_value_score >= q_score) & (df.churn_risk >= q_risk),
        (df.growth_potential >= q_growth) & (df.high_value_score < q_score),
    ], ["Premium recorrente", "Corporativo em risco", "Lazer de alto potencial"], default="Influenciador de experiência")
    df["priority"] = np.select([(df.high_value_score >= q_score) & (df.churn_risk >= q_risk), (df.high_value_score >= df.high_value_score.quantile(.45))], ["P1 - agir agora", "P2 - desenvolver"], default="P3 - observar")
    df["next_best_action"] = np.select([
        df.segment.eq("Corporativo em risco"), df.segment.eq("Premium recorrente"), df.segment.eq("Lazer de alto potencial")
    ], ["Recuperar preferência com benefício controlado e parceiro de mobilidade", "Proteger e encantar com experiência premium", "Desenvolver com experiência vinculada à rota favorita"], default="Transformar engajamento em preferência")
    df["evidence"] = df.apply(lambda r: f"score {r.high_value_score:.0f}; risco {r.churn_risk:.2f}; recência {r.recency_days} dias; rota {r.route}", axis=1)
    return df


def main():
    for p in [RAW, TREATED, ANALYTICS]: p.mkdir(parents=True, exist_ok=True)
    df = build()
    df.to_csv(RAW / "customers.csv", index=False)
    df.to_parquet(ANALYTICS / "customer_features.parquet", index=False)
    df.to_csv(ANALYTICS / "customer_features.csv", index=False)
    print(f"MVP generated: {len(df)} customers; {df.segment.nunique()} segments; {(df.priority == 'P1 - agir agora').sum()} P1")


if __name__ == "__main__": main()
