# fidelidade-copilot

MVP do **Azul CRM de Alto Valor** para o Hack a Business Azul.

> Este protótipo usa somente dados sintéticos. Scores, CLV, churn e propostas de parceiros são hipóteses para demonstração e não representam dados reais nem acordos comerciais.

## Objetivo

Identificar clientes de alto valor atual ou futuro, estimar risco de evasão, explicar a prioridade e recomendar uma próxima melhor ação de CRM com aprovação humana.

## Stack rápida

- Python 3.11+
- pandas, NumPy, scikit-learn e Parquet
- Streamlit para o dashboard
- Plotly/Streamlit para visualização
- Evolução prevista: DuckDB, FastAPI, LangGraph, Pydantic, SHAP e testes pytest

## Execução local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py
streamlit run app.py
```

## Estrutura

- `data/raw`: snapshot sintético de origem
- `data/treated`: reservado para dados tratados
- `data/analytics`: features, scores, segmentos e recomendações
- `pipeline.py`: geração e materialização da base
- `app.py`: dashboard Streamlit
- `docs`: documentação complementar
- `tests`: testes automatizados

## Regras de responsabilidade

O agente futuro deverá consultar apenas ferramentas permitidas, produzir JSON validado, mostrar evidências e solicitar aprovação humana. O dashboard deve continuar funcionando com fallback determinístico por regras quando o LLM falhar.
