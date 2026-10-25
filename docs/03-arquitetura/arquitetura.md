# Arquitetura

O MVP separa a origem sintética, o tratamento e a camada analítica. O pipeline gera features de valor, frequência, recência, potencial, experiência e engajamento. O score combina essas dimensões; o churn usa uma regressão logística baseline; a segmentação aplica regras explícitas.

A interface Streamlit consulta somente a camada analytics. A recomendação atual é determinística e funciona sem LLM. Na próxima evolução, LangGraph poderá orquestrar ferramentas limitadas com Pydantic/JSON Schema e aprovação humana.

## Limitações

- Nenhum dado real da Azul é utilizado.
- Pesos e thresholds são hipóteses iniciais.
- O churn não é uma previsão validada temporalmente.
- Parceiros são hipóteses sujeitas a contrato, estoque e elegibilidade.
