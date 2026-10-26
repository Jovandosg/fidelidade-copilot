# fidelidade-copilot

MVP do **Azul CRM de Alto Valor** ("Âncora Azul") para o Hack a Business Azul.

> Este protótipo usa somente dados sintéticos. Scores, CLV, churn e propostas de parceiros são hipóteses para demonstração e não representam dados reais nem acordos comerciais. Não há previsão validada.

## Objetivo

Identificar clientes de alto valor atual ou futuro, estimar risco de evasão, explicar a prioridade e recomendar uma próxima melhor ação de CRM com aprovação humana.

## Arquitetura

```
src/pipeline (gerador sintético + modelos HVS/risco/NBA, validado por docs/02-dados/data_contracts.yml)
      └─► data/analytics/*.csv ──► src/db (migrações + upsert) ──► PostgreSQL (schema analytics)
                                                                       └─► API FastAPI somente leitura (papel SELECT)
                                                                              └─► Frontend React 19 + Vite + Tailwind + ApexCharts
```

O contrato de dados (`docs/02-dados/data_contracts.yml`, v1.1.0) é a fonte da verdade: pandera, DDL do Postgres e schemas Pydantic são verificados contra ele em `tests/test_parity.py`.

## Pré-requisitos

Python 3.11+, Node 20+ (testado com 24), Docker (Desktop) e PowerShell.

## Execução rápida (um comando)

```powershell
.\scripts\start.ps1
```

O script: cria `.env` com senhas aleatórias se não existir → sobe o Postgres (docker) → instala dependências → gera os dados e valida → aplica migrações e carrega no banco → sobe a API em http://localhost:8000/docs e o frontend em http://localhost:5173. `Ctrl+C` encerra API e frontend (o Postgres continua no Docker; `docker compose down` para parar).
`.\scripts\start.ps1 -SetupOnly` prepara banco e dados e sai, sem subir os servidores.

> O script é PowerShell. Em Linux/macOS, use os passos manuais abaixo.

## Passo a passo manual

```bash
python -m venv .venv && source .venv/bin/activate     # no Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # troque as senhas; .env não é versionado
docker compose up -d            # postgres:16, somente em 127.0.0.1
python -m src.pipeline          # gera/valida data/raw, data/treated, data/analytics
python -m src.db all            # migrações versionadas + carga idempotente (upsert)
uvicorn src.api.main:app --port 8000
cd frontend && npm install && npm run dev
```

Exporte as variáveis do `.env` no shell (`DATABASE_URL`, `DATABASE_URL_RO`, `CORS_ORIGINS`) antes de rodar `src.db` e a API.

## Testes

```powershell
.\scripts\test.ps1     # pytest + tsc + vitest
```

- `pytest -q`: pipeline, contrato, modelos e paridade (contrato × pandera × DDL × Pydantic) rodam sempre. Testes de banco e de API (`tests/test_db.py`, `tests/test_api.py`) usam um banco temporário descartável e são **pulados** sem `DATABASE_URL`/`DATABASE_URL_RO`.
- `cd frontend && npm test`: vitest (cliente da API, formatação e fluxos das telas, com ApexCharts simulado). `npm run build` roda `tsc` e o build do Vite.

## API somente leitura

Somente GET, paginada, sem PII, conectando com o papel `fidelidade_ro` (apenas SELECT) via `DATABASE_URL_RO`: `/kpis`, `/clientes` (filtros `profile`, `segment`, `min_risk`, `max_risk`, `sort`, `desc`), `/clientes/{id}`, `/rotas`, `/nba`. CORS restrito a `CORS_ORIGINS` (padrão `http://localhost:5173`).

Tipos TypeScript: `scripts/gen_types.ps1` gera `frontend/openapi.json` e `frontend/src/api/schema.d.ts` a partir da API (um teste falha se o `openapi.json` ficar desatualizado).

## Telas

Visão Executiva, Mapa Valor × Risco, Fila de Risco, Perfil do Cliente (explicação do HVS e do risco) e Próxima Melhor Ação (com aviso de aprovação humana). O front só consome a API.

## Solução de problemas

- `db/init/*.sh` precisa de finais de linha LF (garantido por `.gitattributes`); com CRLF o container não cria o login da API. Se o volume foi criado assim, rode `docker compose down -v` e suba de novo.
- Porta 5432 ocupada: defina `POSTGRES_PORT` e as URLs no `.env`.
- Senha do banco mudou depois da primeira subida: as senhas só valem na criação do volume; use `docker compose down -v` (apaga os dados locais, que são sintéticos e reproduzíveis).

## Limitações conhecidas

- O gerador sintético não tem dinâmica de churn: o ROC-AUC do radar de risco no hold-out é baixo (≈0,58) e poucos clientes caem no quadrante valor alto + risco alto. Os números ilustram o fluxo, não desempenho real.
- A API abre uma conexão por requisição (sem pool).
- O bundle do frontend tem ~850 kB (ApexCharts) e não usa code-splitting.

## Estrutura

- `data/raw`: snapshot sintético de origem
- `data/treated`: reservado para dados tratados
- `data/analytics`: features, scores, segmentos e recomendações
- `src/`: pipeline oficial (gerador, transformação, validação pelo contrato), `models/`, `db.py`, `api/`
- `db/`: migrações SQL versionadas e init do container
- `frontend/`: dashboard React
- `scripts/`: `start.ps1`, `test.ps1`, `export_openapi.py`, `gen_types.ps1`
- `legacy/`: MVP antigo (Streamlit) preservado por histórico; não executar
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
