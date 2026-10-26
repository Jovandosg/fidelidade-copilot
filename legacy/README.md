# legacy/

Arquivos do MVP antigo (Streamlit), preservados por historico. **Nao executar**: os caminhos internos nao foram mantidos e o `pipeline_mvp_antigo.py` gera IDs `SYN-` fora do contrato `docs/02-dados/data_contracts.yml`.

| Arquivo | Origem | Motivo |
|---|---|---|
| `pipeline_mvp_antigo.py` | `pipeline.py` (raiz) | Pipeline paralelo ao `src/`; schema diferente do contrato (`high_value_score`, `churn_risk`, `clv`...). |
| `app_streamlit.py` | `app.py` (raiz) | Dashboard que le colunas inexistentes no pipeline oficial; sera substituido por React + API. |
| `run_streamlit.sh` | `run.sh` (raiz) | Subia o pipeline antigo e o Streamlit. |
| `customer_features_mvp_antigo.parquet` | `data/analytics/` | Schema obsoleto, divergente do CSV e do contrato. |
| `requirements-legacy.txt` | `requirements.txt` | Dependencias so do legado (`streamlit`). |

Fonte de verdade atual: `src/` + `docs/02-dados/data_contracts.yml`. Origem no git: commit `2373d25` (e anteriores); o historico dos arquivos e preservado por `git mv`.
