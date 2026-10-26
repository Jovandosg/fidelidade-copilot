# Agente de próxima melhor ação (simulado)

> Dados sintéticos. O agente **sugere**; nunca ativa nada. Toda proposta exige aprovação humana (perfil `gestor`) e fica em trilha de auditoria imutável.

## Objetivo
Responder perguntas do analista e propor a ação de CRM de um cliente com **fonte pública citada**, dentro de um teto de benefício e só se o cliente for elegível.

## Fluxo

```
Pergunta ─► check_input (sanitiza PII, detecta injeção) ──bloqueio──► recusa padrão (sem ferramentas)
        └─► ferramentas tipadas (somente leitura): consultar_cliente · calcular_elegibilidade · buscar_regra (RAG)
        └─► provider (LLM opcional | RulesProvider determinístico)
        └─► check_output (schema, citação, PII, teto de benefício, elegibilidade, sem "ativei") ──violação──► fallback por regras
        └─► (se ação) ops.agent_proposals = pending + audit_log ─► gestor aprova/rejeita ─► audit_log
```

## Componentes (`src/agent`, `src/knowledge`)
| Arquivo | Papel |
|---|---|
| `tools.py` | `Toolbox`: 3 ferramentas com schema Pydantic estrito; valida antes de tocar o banco; sem SQL livre. Conexão `fidelidade_ro` (SELECT). |
| `providers.py` | `RulesProvider` (padrão) e `HttpLLMProvider` (chave só por env). Sem credencial, cai em regras. |
| `guardrails.py` | Entrada (8 famílias de injeção, PII redigida) e saída (violações por código). Host de fonte permitido: `voeazul.com.br` e subdomínios, https. |
| `orchestrator.py` | `Agent.ask`: orquestra e aplica o fallback (`no_credential`, `provider_error`, `guardrail_violation`). |
| `evals.py`, `eval_cases.py` | Harness: casos felizes, adversariais e sem fonte; mede groundedness, violações e taxa de fallback. |
| `src/knowledge`, `knowledge/sources/*.md` | RAG: fontes públicas versionadas (`public_sources`, URL e data de consulta), chunking com metadados, embeddings pgvector (`hash-256-v1`, lexical). |

## API (SSE)
`POST /agente/perguntar` e `POST /nba/{id}/proposta` (analista, gestor) · `POST /propostas/{id}/decisao` (gestor) · `GET /propostas/fila/stream` (SSE, reconecta a cada 60 s, máx. 10 streams). Detalhes em [operacao.md](../operacao.md).

## Como rodar (com as variáveis do `.env` carregadas)
```powershell
python -m src.agent.evals             # harness (fallback sem LLM)
python -m pytest tests/test_guardrails.py tests/test_agent_api.py tests/test_redteam.py -q
```

## Habilitar o LLM real (só depois de validar o fallback)
1. `python -m src.agent.evals` e `tests/test_redteam.py` verdes **sem** LLM.
2. No ambiente (nunca no repositório): `AGENT_LLM_PROVIDER=llm`, `AGENT_LLM_API_KEY`, `AGENT_LLM_BASE_URL` (https) e `AGENT_LLM_MODEL`.
3. Rode os evals de novo: fallback e violações não podem piorar. Toda saída do LLM passa pelos mesmos guardrails.

Riscos: [riscos.md](riscos.md) · Red team: [redteam.md](redteam.md)
