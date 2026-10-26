# Plano: Dashboard de observabilidade "Ancora Azul" (analise, viabilidade, 3 arquiteturas e prompts)

## 1. Diagnostico do repositorio (estado real hoje)

**O que existe**
- `src/` (pipeline "oficial", testado): `generator.py` (1.200 clientes `C000001`, ~6,7 mil transacoes, seed 20261014), `transform.py` (value_score 0-100, 4 segmentos, acao fixa por segmento), `validation.py` (pandera + `quality_report.json`), `pipeline.py`. `tests/test_pipeline.py` cobre apenas esse fluxo.
- Raiz: `pipeline.py` + `app.py` (Streamlit) = MVP "antigo" com `high_value_score`, `churn_risk` (LogisticRegression), `clv`, `priority`, `evidence`, `next_best_action`.
- Dados: `data/raw|treated|analytics` (CSV/Parquet), 100% sinteticos, sem PII.
- Docs organizados em `docs/00..04` + PDF da pesquisa "Ancora Azul".

**Problemas encontrados (afetam viabilidade e precisao)**
1. **Dois pipelines divergentes.** `app.py` le colunas (`high_value_score`, `churn_risk`, `clv`, `priority`, `evidence`, `next_best_action`) que o pipeline testado em `src/` NAO gera. O `pipeline.py` da raiz tambem sobrescreve `data/raw/customers.csv` com outro schema (IDs `SYN-`, nao `C000000`) e quebra `data_contracts.yml`/pandera. Hoje `run.sh` + `app.py` nao funcionam com os dados versionados.
2. **Pilares da Ancora Azul so 25% cobertos no codigo testado:** Identificar = value_score simples (RFV+tier, sem BG/NBD x Gamma-Gamma, sem perfis A-E, sem IVR); Proteger = so "recencia > 180d" (sem Radar de Risco, sem disrupcao x valor); Crescer/NBA = lookup estatico por segmento (sem uplift/bandit); Surpreender/Agente = inexistente (sem RAG, sem guardrails).
3. **Churn circular:** no pipeline da raiz o rotulo `churn_label` e derivado das mesmas variaveis usadas para treinar (recencia, reclamacoes, frequencia) e avaliado no treino -> AUC inflado, nao valida. Precisa de rotulo temporal (janela futura) ou ser rotulado como "score heuristico".
4. **Sem sinais de experiencia:** o gerador atual nao tem atrasos/cancelamentos por rota/voo, reclamacoes, canal, saldo de pontos, margem/ancillaries -> sem isso o Radar de Risco ("disrupcao sofrida x valor") e a observabilidade de rota (IVR) nao sao computaveis. ANAC VRA/consumidor.gov so documentados em `public_sources.md`, nao ingeridos.
5. **Contratos rigidos:** `len == 1200` hardcoded na validacao; sem versionamento de execucao/modelo.
6. **Stack:** nao ha Node/Vite/React, API, Postgres, nem container. `requirements.txt` tem pacotes duplicados/sobrepostos (pandas e pytest 2x) e `streamlit` (fora da stack pedida). Faltam para a pesquisa: `lifetimes`/implementacao propria de BG/NBD+GG, `shap`, `fastapi`, `uvicorn`, `sqlalchemy`/`psycopg`, `pydantic`.
7. **Versao:** "React 19.3" - confirmar que existe no npm; a estavel que conheco e 19.2.x (ApexCharts tem `react-apexcharts` compativel com 19).

**Veredito de viabilidade:** VIAVEL como MVP de hackathon **se** a Fase 0 (consolidar o pipeline em `src/` e alinhar contrato de dados) vier primeiro. Sem ela, qualquer dashboard sera construido sobre dados incoerentes. Dados reais da Azul nao existem: o dashboard deve ser rotulado "simulado / calibrado com ANAC", nunca como previsao validada.

## 1.1 Regra de arquitetura (decisao do usuario)
As novas colunas da Ancora Azul (HVS e componentes, risco/Radar, NBA, sinais de disrupcao, IVR) devem ser **persistidas no PostgreSQL**, e o front so recebe dados **via API** (React -> FastAPI -> Postgres). O front nunca le CSV/Parquet.
Fluxo unico: `contrato (data_contracts.yml v1.1.0) -> src/ gera e valida (pandera) -> carga idempotente no Postgres (analytics.*) -> FastAPI le do Postgres -> React/ApexCharts`.
Parquet/CSV ficam apenas como artefatos de auditoria/reprodutibilidade. Cada coluna nova precisa existir nos 4 lugares: contrato, pandera, tabela Postgres (migracao SQL) e schema Pydantic da API (e tipo TypeScript no front). Um teste de paridade deve falhar se algum desses divergir.

## 2. Mapa Ancora Azul -> telas do dashboard

| Pilar | Modelo/regra | Tela de observabilidade |
|---|---|---|
| Identificar | HVS = CLV (BG/NBD x Gamma-Gamma) x estabilidade x margem - custo de servir; perfis A-E; IVR por rota | Visao executiva, mapa valor x risco, ranking de rotas (IVR), perfis |
| Proteger | Radar de Risco (disrupcao x valor), GBM/Survival + explicacao | Fila de risco priorizada, drill-down por cliente (SHAP/fatores) |
| Crescer | NBA (regras -> uplift/bandit depois) | Fila de NBA com custo/margem esperada e aprovacao humana |
| Surpreender | Regras + LLM para copy, RAG nas regras Azul Fidelidade | Painel do Agente (resposta + fontes + guardrails) |
| Transversal (observabilidade) | Qualidade de dados, drift (PSI), saude do modelo, auditoria | Tela "Saude da plataforma" |

## 3. Tres arquiteturas propostas

### Arquitetura A - "Lean": Batch Python -> Postgres -> FastAPI (read-only) -> React
- Fluxo: `src/` gera/transforma/pontua -> grava `analytics.*` no Postgres (e Parquet) -> FastAPI so leitura -> React 19 + Vite + Tailwind + ApexCharts.
- NBA por regras; agente deterministico com fallback (sem LLM obrigatorio).
- Por que: menor risco, entrega visual rapida, reutiliza ~80% do codigo atual, ideal para iniciantes e prazo curto.
- Contras: pouca "observabilidade" real e sem diferencial de IA; Postgres quase so como armazenamento.
- Viabilidade: ALTA. Risco: baixo.

### Arquitetura B - "Observavel": Medallion em Postgres + monitoramento de modelo e dados + auditoria
- Fluxo: schemas `raw/treated/analytics/ops`; `ops.pipeline_runs`, `ops.data_quality_results` (pandera), `ops.model_registry`, `ops.drift_metrics` (PSI), `ops.audit_log` (aprovacoes). FastAPI com RBAC simples (analista/gestor/auditor), mascaramento de dados, rate limit. Dashboard com aba "Saude da plataforma".
- Por que: e a leitura mais fiel de "dashboard de observabilidade" e conversa com Blue Team (trilha de auditoria, least privilege, logs imutaveis, sem PII, headers/CSP).
- Contras: mais tabelas e mais codigo; precisa dos sinais de disrupcao (Fase 0 maior).
- Viabilidade: MEDIA-ALTA. Risco: medio.

### Arquitetura C - "Agente-central": B + RAG (pgvector) + agente com guardrails + fila de aprovacao em tempo real
- Fluxo: documentos de regras do Azul Fidelidade (publicos) -> chunks + embeddings em `pgvector` -> agente (provider abstrato LLM, com fallback por regras) responde/explica/gera copy; saida validada por Pydantic + policy engine (elegibilidade, teto de beneficio, sem PII, aprovacao humana obrigatoria); fila de aprovacoes via SSE no React; avaliacoes (evals) de groundedness e violacao de guardrails.
- Por que: e o diferencial pedido pelo desafio (IA no centro) e ja alinhado ao seu papel (Agent/Harness/Guardrails).
- Contras: maior superficie de ataque (prompt injection, vazamento), custo/credenciais de LLM, tempo de avaliacao.
- Viabilidade: MEDIA. Risco: alto sem A/B como base.

**Recomendacao:** executar A como base -> evoluir para B -> C. Os prompts abaixo sao independentes, mas B e C assumem a Fase 0 da A (Task 1-2).

## 4. Prompts (estrutura pedida) - ver resposta final no chat e abaixo

Cada prompt tem Tasks atomicas; executar UMA por vez, validando antes da proxima.

### PROMPT A - Lean

```
[ROLE]
Atue como Desenvolvedor Full Stack senior (Python, React 19, Vite, Tailwind, ApexCharts, PostgreSQL) com nocoes de seguranca Blue Team, no repositorio fidelidade-copilot.

[TASK]
Task1 - Consolidar o pipeline: tornar src/ a unica fonte da verdade. Decidir se app.py/pipeline.py da raiz serao removidos ou movidos para legacy/ (propor antes de apagar). Motivo: hoje o pipeline da raiz grava IDs `SYN-` e colunas fora do contrato nos mesmos caminhos de data/raw e data/analytics, quebrando o que a API/Postgres/React vao consumir. Tratar docs/02-dados/data_contracts.yml (v1.0.0, Pessoa 1/2) como a fonte da verdade do formato dos dados: (a) verificar que raw/treated/analytics hoje o cumprem; (b) como a Ancora Azul exige novas colunas (HVS, risco, NBA, sinais de disrupcao), PROPOR a evolucao do contrato (version 1.1.0 + changelog) e aprova-la ANTES de implementar; (c) manter src/validation.py (pandera) alinhado ao contrato, idealmente gerado/lido a partir dele, sem duplicar regras a mao. Garantir que `pytest` passe.
Task2 - Enriquecer o gerador com sinais necessarios (atrasos/cancelamentos por rota, reclamacoes, canal, saldo de pontos, margem) mantendo seed fixa e sem PII; atualizar contrato, dicionario de dados e pandera (remover o `== 1200` hardcoded).
Task3 - Implementar src/models: HVS explicavel (componentes visiveis), Radar de Risco (GradientBoosting com rotulo temporal, avaliacao em hold-out), NBA por regras com custo/margem. Salvar metricas.
Task4 - Criar o schema Postgres (analytics.*) com migracoes SQL versionadas, contendo TODAS as colunas novas do contrato v1.1.0 (hvs, componentes do hvs, risk_score, risk_drivers, nba_action, nba_expected_margin, disruption_*, ivr por rota). Carga idempotente (upsert) a partir do pipeline e usando docker-compose para o Postgres local. Teste de paridade: contrato x pandera x tabela Postgres x schema Pydantic.
Task5 - Criar API FastAPI somente leitura que consulta o Postgres (nunca arquivos): /kpis, /clientes, /clientes/{id}, /rotas, /nba, com Pydantic espelhando as colunas do Postgres, paginacao, CORS restrito e sem PII. Gerar os tipos TypeScript a partir do OpenAPI.
Task6 - Criar frontend Vite + React 19 + Tailwind + react-apexcharts, consumindo apenas a API (tipos gerados do OpenAPI): Visao Executiva, Mapa Valor x Risco, Fila de Risco, Perfil do Cliente (explicacao), NBA com aviso de aprovacao humana.
Task7 - Testes (pytest + vitest), README de execucao e script unico de subida.

[CONSTRAINTS]
- Nao apagar nem sobrescrever arquivos existentes sem listar e pedir confirmacao.
- Dados sinteticos rotulados como tais; nada de promessas de previsao validada.
- Sem segredos no repo (.env.example). Queries parametrizadas. Usuario do banco da API com permissao apenas SELECT.
- Python conforme requirements.txt (limpar duplicatas); React 19.x (confirmar versao no npm).
- Fazer apenas a Task solicitada por vez.

[OUTPUT]
Para cada Task: arquivos criados/alterados, comandos de verificacao executados e resultado, riscos remanescentes e proxima Task sugerida.

[OBS]
Responder em portugues. Parar ao final de cada Task e aguardar aprovacao. Commit por Task com Co-authored-by padrao.
```

### PROMPT B - Observavel

```
[ROLE]
Atue como Desenvolvedor Full Stack senior e engenheiro de dados/MLOps com foco em seguranca defensiva (Blue Team), stack Python + PostgreSQL + FastAPI + React 19/Vite/Tailwind/ApexCharts.

[TASK]
Task1 - Executar a consolidacao do pipeline em src/ (mesmo escopo da Task1 e Task2 do Prompt A) e fechar o contrato de dados.
Task2 - Modelar Postgres em camadas: schemas raw, treated, analytics, ops. As colunas novas da Ancora Azul (HVS e componentes, risco e drivers, NBA, disrupcao, IVR) devem ser persistidas em analytics.* e servidas ao front somente pela API; teste de paridade contrato x pandera x Postgres x Pydantic. Criar tabelas ops.pipeline_runs, ops.data_quality_results, ops.model_registry, ops.drift_metrics, ops.audit_log (append-only via trigger/permissoes).
Task3 - Instrumentar o pipeline: cada execucao grava run_id, duracao, linhas, resultado pandera por regra, versao de codigo/seed.
Task4 - Modelos (HVS, Radar de Risco, NBA) registrados no model_registry com metricas, data de treino e hash dos dados; calcular PSI/drift por feature entre execucoes e alertas por limiar.
Task5 - API FastAPI com RBAC (analista/gestor/auditor) por token JWT, rate limit, logs estruturados, headers de seguranca e endpoint de aprovacao que escreve em audit_log (quem, quando, o que, antes/depois).
Task6 - Frontend: abas Executivo, Proteger (Radar), Crescer (NBA + aprovacao), Rotas (IVR), Saude da plataforma (qualidade, drift, modelos, execucoes, auditoria).
Task7 - Testes (pytest, contrato, seguranca basica de API) e documentacao de operacao em docs/03-arquitetura.

[CONSTRAINTS]
- Nada de PII; ids sinteticos. Principio do menor privilegio: roles separadas de banco (etl, api_ro, api_audit).
- Migracoes SQL versionadas e idempotentes. Sem segredos no repo.
- Nao apagar arquivos existentes sem confirmacao. Uma Task por vez.
- Metricas de modelo sempre com ressalva de dados sinteticos.

[OUTPUT]
Por Task: diff resumido, evidencias (saida de testes/queries), decisoes e riscos, e checklist de seguranca atendido.

[OBS]
Portugues. Aguardar aprovacao entre Tasks. Se a Task1 ja foi feita, apenas validar.
```

### PROMPT C - Agente-central

```
[ROLE]
Atue como Desenvolvedor Full Stack senior e engenheiro de agentes de IA com mentalidade Blue Team (prompt injection, exfiltracao, abuso de ferramentas), stack Python + PostgreSQL/pgvector + FastAPI + React 19/Vite/Tailwind/ApexCharts.

[TASK]
Task1 - Garantir a base conforme Prompts A/B (pipeline consolidado, colunas novas persistidas no Postgres e servidas ao front via API); so validar se ja existir. As propostas e decisoes do agente tambem devem ser persistidas no Postgres (tabelas de propostas e audit_log) e lidas pelo front via API.
Task2 - Criar a base de conhecimento do RAG: coletar apenas regras publicas do Azul Fidelidade (URLs e data de consulta em public_sources), chunking com metadados, embeddings em pgvector, versionamento da fonte.
Task3 - Implementar src/agent: ferramentas limitadas (consultar cliente, calcular elegibilidade, buscar regra) com schemas Pydantic; provider de LLM abstrato com fallback deterministico por regras quando o LLM falhar ou nao houver credencial.
Task4 - Guardrails/policy engine: entrada (sanitizacao, deteccao de prompt injection), saida (JSON Schema, citacao obrigatoria de fonte, sem PII, teto de beneficio, elegibilidade) e aprovacao humana obrigatoria antes de qualquer ativacao.
Task5 - Harness de avaliacao: conjunto de casos (feliz, adversarial, sem fonte) medindo groundedness, violacoes de guardrail e taxa de fallback; rodar no pytest.
Task6 - API: endpoints /agente/perguntar e /nba/{id}/proposta com streaming SSE; fila de aprovacoes com audit_log.
Task7 - Frontend: painel do Agente (resposta, fontes citadas, status dos guardrails), fila de aprovacao em tempo real e badge "simulado".
Task8 - Teste de seguranca (red team basico), documentacao e checklist de riscos em docs/03-arquitetura/agente.

[CONSTRAINTS]
- O agente nunca executa ativacao sozinho; sem acesso direto ao banco (somente ferramentas tipadas).
- Chaves de API apenas por variavel de ambiente; nada no repo. Logs sem conteudo sensivel.
- Fontes somente publicas e citadas. Nao inventar regras de negocio.
- Nao apagar arquivos existentes sem confirmacao. Uma Task por vez.

[OUTPUT]
Por Task: arquivos, comandos e resultados dos testes/evals, riscos abertos, proxima Task.

[OBS]
Portugues. Validar o fallback sem LLM antes de habilitar o provider real. Aguardar aprovacao entre Tasks.
```

## 5. Todos
- fase0-consolidar-pipeline (pre-requisito de A/B/C)
- escolher arquitetura (recomendado A -> B -> C)
- executar prompts por Task, com aprovacao entre elas

## 6. Notas
- Nenhum arquivo do repositorio foi alterado nesta analise.
- Confirmar versao do React (19.3) no npm antes da Task de frontend.
