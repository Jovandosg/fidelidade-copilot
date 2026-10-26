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

- Python 3.11+, Node 20+ (testado com 24) e Docker (Desktop) **em execução**.
- PowerShell (Windows) para o script de subida; em Linux/macOS use o passo a passo manual.
- Você precisa estar numa branch/commit que contenha `src/db.py` e `src/api/` (branch `Dev_Agent_harness&guardrails` ou posterior). Em versões antigas, `python -m src.db` e `uvicorn src.api.main:app` falham com "No module named".
- Rode todos os comandos **na raiz do repositório**.

## Execução rápida (um comando, Windows)

```powershell
git checkout "Dev_Agent_harness&guardrails"; git pull
.\scripts\start.ps1
```

O script: cria `.env` com senhas aleatórias se não existir → sobe o Postgres (docker) e espera ficar `healthy` → instala dependências → gera os dados e valida → aplica migrações e carrega no banco → sobe a API e o frontend.

| Serviço | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| API (docs interativas) | http://localhost:8000/docs |
| KPIs (teste rápido) | http://localhost:8000/kpis (exige token JWT; veja "API (JWT + RBAC)") |

A API não tem rota em `/`: o `404` em `GET /` é esperado. `Ctrl+C` encerra API e frontend; o Postgres continua no Docker (`docker compose down` para parar).
`.\scripts\start.ps1 -SetupOnly` prepara banco e dados e sai, sem subir os servidores.

## Passo a passo manual (qualquer SO)

Importante: `python -m src.db` e a API **não leem o arquivo `.env`**; leem variáveis de ambiente. Por isso o passo 4 exporta o `.env` no terminal. Faça isso em cada terminal novo.

**1. Dependências**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configuração** (o `.env` não é versionado)
```powershell
Copy-Item .env.example .env         # Linux/macOS: cp .env.example .env
```
Edite o `.env`: troque as senhas. `POSTGRES_PORT` e as URLs (`DATABASE_URL`, `DATABASE_URL_RO`, `DATABASE_URL_ETL`, `DATABASE_URL_AUDIT`) devem usar a mesma porta e as senhas correspondentes.

**3. Banco**
```powershell
docker compose up -d
docker ps                           # aguarde "Up (healthy)"
```

**4. Carregar o `.env` no terminal**
```powershell
# PowerShell
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=\s][^=]*)=(.*)$') { Set-Item "env:$($matches[1].Trim())" $matches[2].Trim() } }
```
```bash
# Linux/macOS
set -a; source .env; set +a
```

**5. Dados, migrações e carga**
```powershell
python -m src.pipeline              # gera/valida data/raw, data/treated, data/analytics
python -m src.db all                # migrações versionadas + carga idempotente (upsert)
```
Leva poucos segundos. Se travar, o `DATABASE_URL` não bate com o container (veja a solução de problemas).

**6. API e frontend** (dois terminais, ambos com o `.env` carregado no da API)
```powershell
uvicorn src.api.main:app --port 8000
cd frontend; npm install; npm run dev
```

**Recriar tudo do zero** (os dados são sintéticos e reproduzíveis):
```powershell
docker compose down -v; Remove-Item .env
.\scripts\start.ps1
```

## Testes

```powershell
.\scripts\test.ps1     # pytest + tsc + vitest
```

- `pytest -q`: pipeline, contrato, modelos e paridade (contrato × pandera × DDL × Pydantic) rodam sempre. Testes de banco e de API (`tests/test_db.py`, `tests/test_api.py`) usam um banco temporário descartável e são **pulados** sem `DATABASE_URL`/`DATABASE_URL_RO`.
- `cd frontend && npm test`: vitest (cliente da API, formatação e fluxos das telas, com ApexCharts simulado). `npm run build` roda `tsc` e o build do Vite.

## API (JWT + RBAC)

Toda rota exceto `/health` exige `Authorization: Bearer <jwt>`. Gere um token local (usa `JWT_SECRET` do `.env`, ≥ 32 caracteres; sem ele a API responde 503 e nada é liberado):

```powershell
python -m src.api.tokens --sub seu.apelido --role gestor   # analista | gestor | auditor; --hours até 24
```

| Perfil | Pode |
|---|---|
| `analista` | ler `/kpis`, `/clientes`, `/rotas`, `/nba`, `/ops/*` |
| `gestor` | tudo do analista + `POST /nba/{id}/aprovacao` e `GET /nba/aprovacoes` |
| `auditor` | leitura + `GET /audit` (trilha) e `GET /nba/aprovacoes`; não aprova |

Dados em `analytics`/`ops` via `fidelidade_ro` (somente SELECT, `DATABASE_URL_RO`); a aprovação e a leitura da trilha usam `fidelidade_api_audit` (`DATABASE_URL_AUDIT`, INSERT/SELECT só em `ops.audit_log`). Cada aprovação grava quem, quando, o quê e antes/depois (decisão única por cliente; a trilha é imutável). Sem PII: `sub` é um apelido e a justificativa não deve conter dados pessoais.

Endpoints: `/kpis`, `/clientes` (filtros `profile`, `segment`, `min_risk`, `max_risk`, `sort`, `desc`), `/clientes/{id}`, `/rotas`, `/nba`, `/ops/runs`, `/ops/quality`, `/ops/models`, `/ops/drift`, `/audit`. Proteções: rate limit por IP (`RATE_LIMIT_PER_MINUTE`=120 leitura, `RATE_LIMIT_WRITE_PER_MINUTE`=20 escrita; em memória, por processo → 429 com `Retry-After`), logs JSON por requisição (`request_id`, status, duração, `sub`/`role`; sem query string nem token), headers de segurança (CSP, nosniff, X-Frame-Options, HSTS, no-store) e CORS restrito a `CORS_ORIGINS`.

> **Frontend:** ao abrir `http://localhost:5173` informe o token (colado na tela de entrada; fica só no `sessionStorage` da aba e vai apenas no cabeçalho `Authorization`). As abas são Executivo, Proteger (Radar), Crescer (NBA + aprovação, só o perfil gestor decide), Rotas (IVR) e Saúde da plataforma (execuções, qualidade, drift, modelos e, só para o auditor, a trilha de auditoria). Token inválido/expirado (401) devolve à tela de entrada.

Tipos TypeScript: `scripts/gen_types.ps1` gera `frontend/openapi.json` e `frontend/src/api/schema.d.ts` a partir da API (um teste falha se o `openapi.json` ficar desatualizado).

## Telas

Visão Executiva, Mapa Valor × Risco, Fila de Risco, Perfil do Cliente (explicação do HVS e do risco) e Próxima Melhor Ação (com aviso de aprovação humana). O front só consome a API.

## Solução de problemas

- `db/init/*.sh` precisa de finais de linha LF (garantido por `.gitattributes`); com CRLF o container não cria o login da API. Se o volume foi criado assim, rode `docker compose down -v` e suba de novo.
- `No module named src.db` ou `src.api`: você está numa branch antiga ou fora da raiz do repositório. Atualize a branch (veja Pré-requisitos).
- `python -m src.db all` trava ou `DATABASE_URL nao definido`: o terminal não tem as variáveis do `.env` ou a porta/senha da URL não bate com o container. Rode o passo 4 do manual, confira `echo $env:DATABASE_URL` e `docker ps`, ou use `.\scripts\start.ps1`.
- API responde 500 em `/kpis`: o banco está vazio ou inacessível; rode `python -m src.db all`.
- Porta 5432 ocupada (outro Postgres local): defina `POSTGRES_PORT=55432` e use essa porta em `DATABASE_URL` e `DATABASE_URL_RO` no `.env`.
- Senha do banco mudou depois da primeira subida: as senhas só valem na criação do volume; use `docker compose down -v` (apaga os dados locais, que são sintéticos e reproduzíveis).

## Limitações conhecidas

- O gerador sintético não tem dinâmica de churn: o ROC-AUC do radar de risco no hold-out é baixo (≈0,58) e poucos clientes caem no quadrante valor alto + risco alto. Os números ilustram o fluxo, não desempenho real.
- A API abre uma conexão por requisição (sem pool).
- O bundle do frontend tem ~850 kB (ApexCharts) e não usa code-splitting.

## Camadas do banco e papéis

| Schema | Conteúdo | Quem escreve | Quem lê |
|---|---|---|---|
| `raw` | snapshot sintético de origem (`customers`, `transactions`) | `fidelidade_etl` | só dono/etl |
| `treated` | dados tratados | `fidelidade_etl` | só dono/etl |
| `analytics` | features, HVS, risco, NBA, rotas (contrato v1.1.0) | `fidelidade_etl` | `fidelidade_ro` (API) |
| `ops` | `pipeline_runs`, `data_quality_results`, `model_registry`, `drift_metrics`, `audit_log` | etl (menos `audit_log`) | `fidelidade_ro` (menos `audit_log`) |

`ops.audit_log` é append-only: trigger bloqueia UPDATE/DELETE/TRUNCATE (até para o dono) e `fidelidade_api_audit` só tem INSERT/SELECT nela. As migrações `003`-`006` são idempotentes. Os logins dos 3 papéis são criados por `db/init/01-api-role.sh` só na **primeira** subida do volume: se você já tinha um volume antigo, rode `docker compose down -v` e adicione `POSTGRES_ETL_PASSWORD` e `POSTGRES_AUDIT_PASSWORD` ao `.env` (veja `.env.example`).

**Instrumentação:** cada `python -m src.pipeline` grava `data/analytics/run_report.json` (ignorado pelo git) com `run_id`, duração, linhas por entidade, resultado por regra (pandera + regras cruzadas), `code_version` (commit git, `-dirty` se há alterações; ou `CODE_VERSION`) e `seed`. `python -m src.db load` registra isso em `ops.pipeline_runs` e `ops.data_quality_results` (idempotente por `run_id`) e **não carrega dados** se a última execução falhou.

**Modelos e drift:** cada execução também registra HVS, Radar de Risco e NBA em `ops.model_registry` (versão, data de treino, SHA-256 dos dados tratados, métricas, parâmetros e o aviso de dados sintéticos; único por modelo+versão+hash). O PSI por feature (decis, 11 numéricas + `profile` e `nba_action`) é calculado contra a baseline da execução anterior (`data/analytics/drift_baseline.json`, ignorado pelo git) e gravado em `ops.drift_metrics`; PSI ≥ 0,2 marca `alert` e imprime `ALERTA de drift`. Na primeira execução não há baseline, então não há linhas de drift.

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
