import pandas as pd
import streamlit as st

st.set_page_config(page_title="Azul CRM de Alto Valor", layout="wide")
st.title("Azul CRM de Alto Valor")
st.caption("MVP com dados sintéticos, explicações e aprovação humana")

@st.cache_data
def load():
    return pd.read_parquet("data/analytics/customer_features.parquet")

try:
    df = load()
except FileNotFoundError:
    st.error("Dados não encontrados. Execute: python pipeline.py")
    st.stop()

with st.sidebar:
    st.header("Filtros")
    segment = st.multiselect("Segmento", sorted(df.segment.unique()), default=sorted(df.segment.unique()))
    priority = st.multiselect("Prioridade", sorted(df.priority.unique()), default=sorted(df.priority.unique()))
    min_score = st.slider("Score mínimo", 0, 100, 0)
    min_risk = st.slider("Risco mínimo", 0.0, 1.0, 0.0)

view = df[df.segment.isin(segment) & df.priority.isin(priority) & (df.high_value_score >= min_score) & (df.churn_risk >= min_risk)]
a, b, c, d = st.columns(4)
a.metric("Clientes", len(view)); b.metric("P1 agora", int((view.priority == "P1 - agir agora").sum())); c.metric("CLV médio", f"R$ {view.clv.mean():,.0f}"); d.metric("Risco médio", f"{view.churn_risk.mean():.2f}")

st.subheader("Mapa de prioridade")
st.scatter_chart(view, x="high_value_score", y="churn_risk", color="segment")
st.subheader("Clientes priorizados")
st.dataframe(view[["customer_id", "segment", "priority", "high_value_score", "churn_risk", "clv", "route"]].sort_values(["priority", "high_value_score"], ascending=[True, False]), use_container_width=True, hide_index=True)

if not view.empty:
    selected = st.selectbox("Abrir perfil", view.customer_id.tolist())
    row = view[view.customer_id == selected].iloc[0]
    st.subheader(f"Perfil {selected}")
    st.write(f"**Segmento:** {row.segment}  |  **Prioridade:** {row.priority}  |  **Rota:** {row.route}")
    st.info(f"Evidências: {row.evidence}")
    if st.button("Gerar próxima melhor ação"):
        st.success(row.next_best_action)
        st.write("Parceiro sugerido: mobilidade, hotelaria ou experiência no destino, sujeito a contrato, estoque e elegibilidade.")
        st.warning("A recomendação requer aprovação humana antes de qualquer ativação.")
