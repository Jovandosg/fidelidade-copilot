# fidelidade-copilot

MVP do **Azul CRM de Alto Valor** para o Hack a Business Azul.

> Este protótipo usa somente dados sintéticos. Scores, CLV, churn e propostas de parceiros são hipóteses para demonstração e não representam dados reais nem acordos comerciais.

## Objetivo

Identificar clientes de alto valor atual ou futuro, estimar risco de evasão, explicar a prioridade e recomendar uma próxima melhor ação de CRM com aprovação humana.

## Stack rápida

- Python 3.11+
- pandas, NumPy, scikit-learn e Parquet
- Dashboard: React 19 + Vite + Tailwind + ApexCharts em `frontend/` (consome só a API); MVP Streamlit antigo em `legacy/`
- Plotly para visualização
- Evolução prevista: DuckDB, FastAPI, LangGraph, Pydantic, SHAP e testes pytest

## Execução local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline
```

### PostgreSQL (schema `analytics`)

```bash
cp .env.example .env        # defina senhas locais; .env nao e versionado
docker compose up -d        # postgres:16, somente em 127.0.0.1
python -m src.db all        # migracoes versionadas + carga idempotente (upsert)
```

A API usara o papel `fidelidade_ro` (somente SELECT) via `DATABASE_URL_RO`. Os testes de banco (`tests/test_db.py`) usam um banco temporario e sao pulados sem `DATABASE_URL`.

O dashboard Streamlit antigo foi movido para `legacy/` e nao deve ser executado.

### API somente leitura (FastAPI)

```bash
uvicorn src.api.main:app --port 8000     # usa DATABASE_URL_RO (papel fidelidade_ro, so SELECT); docs em /docs
```

Endpoints (somente GET, paginados, sem PII): `/kpis`, `/clientes` (filtros `profile`, `segment`, `min_risk`, `max_risk`, `sort`, `desc`), `/clientes/{id}`, `/rotas`, `/nba`. CORS restrito a `CORS_ORIGINS` (padrao `http://localhost:5173`).
Tipos TypeScript: `scripts/gen_types.ps1` gera `frontend/openapi.json` e `frontend/src/api/schema.d.ts` (um teste falha se o `openapi.json` ficar desatualizado). `scripts/gen_types.ps1` exige Node 20+.

### Frontend (React 19 + Vite + Tailwind + ApexCharts)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (API em VITE_API_URL, padrao http://localhost:8000)
npm test           # vitest
npm run build      # tsc + vite build
```

Telas: Visao Executiva, Mapa Valor x Risco, Fila de Risco, Perfil do Cliente (explicacao do HVS e do risco) e Proxima Melhor Acao (com aviso de aprovacao humana). O front so consome a API, usando tipos gerados do OpenAPI.

Observacao: `db/init/*.sh` precisa de finais de linha LF (garantido por `.gitattributes`), senao o container nao cria o login da API. Se o volume ja foi criado com a versao quebrada, rode `docker compose down -v` e suba de novo.

## Estrutura

- `data/raw`: snapshot sintético de origem
- `data/treated`: reservado para dados tratados
- `data/analytics`: features, scores, segmentos e recomendações
- `src/`: pipeline oficial (gerador, transformacao, validacao pelo contrato)
- `legacy/`: MVP antigo preservado por historico
- `docs`: documentação complementar
- `tests`: testes automatizados

## Colaboração no GitHub

O projeto usa Issues para User Stories, critérios de aceitação, tasks e impedimentos. A documentação de produto está em `docs/00-contexto/visao-produto.md`, a Definition of Done em `docs/04-processo/definition-of-done.md` e o planejamento do primeiro ciclo em `docs/04-processo/sprints/sprint-01.md`.

Templates de Issues estão em `.github/ISSUE_TEMPLATE/`. Para configurar labels, Issues e o Project em uma conta com permissão de escrita, execute:

```bash
./scripts/setup_github_collaboration.sh
```

O guia completo de permissões, branches, commits, revisão e status do Project está em `docs/04-processo/github-colaborativo.md`.

## Regras de responsabilidade

O agente futuro deverá consultar apenas ferramentas permitidas, produzir JSON validado, mostrar evidências e solicitar aprovação humana. O dashboard deve continuar funcionando com fallback determinístico por regras quando o LLM falhar.
