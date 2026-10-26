# Checklist de riscos do agente (OWASP LLM Top 10)

Legenda: ✅ mitigado e testado · 🟡 parcial · 🔴 aberto.

| OWASP | Risco | Status | Mitigação / evidência |
|---|---|---|---|
| LLM01 | Prompt injection | 🟡 | `check_input` (8 famílias, NFKC/zero-width) + saída validada; ver R-01 |
| LLM02 | Saída insegura / PII | ✅ | JSON Schema estrito, PII bloqueada, front renderiza texto e só links https |
| LLM03 | Base de conhecimento envenenada | 🟡 | só fontes públicas versionadas; instruções a modelos rejeitadas na ingestão; ver R-02 |
| LLM04 | Negação de serviço | 🟡 | 500 caracteres, rate limit POST 20/min/IP, máx. 10 streams; limiter em memória (R-05) |
| LLM05 | Cadeia de suprimentos | 🟡 | sem scan automático de dependências (R-06) |
| LLM06 | Vazamento de informação sensível | ✅ | sem PII; chave só por env; logs sem corpo/cabeçalho; teste de eco de chave |
| LLM07 | Vazamento de system prompt | ✅ | sem segredos no prompt; pedidos de prompt bloqueados |
| LLM08 | Agência excessiva | ✅ | 3 ferramentas de leitura; conexão somente leitura; proposta só `pending`; ativação só humana |
| LLM09 | Alucinação / excesso de confiança | 🟡 | citação obrigatória, teto de benefício, elegibilidade conferida, groundedness nos evals; R-02 |
| LLM10 | Abuso de acesso | ✅ | JWT + RBAC; auditor sem acesso ao agente |

## Riscos abertos
| ID | Risco | Impacto | Ação sugerida | Dono |
|---|---|---|---|---|
| R-01 | Injeção por regex: paráfrases e outros idiomas podem passar | Médio (saída ainda é validada) | classificador dedicado; ampliar corpus | Segurança |
| R-02 | Base sem regras numéricas oficiais (site da Azul respondeu 403) | Alto p/ produção | colar texto oficial em `knowledge/sources/*.md` e reingerir | Produto |
| R-03 | Busca lexical `hash-256-v1`, não semântica | Baixo | embedding real e comparar evals | Dados |
| R-04 | Provider LLM real só simulado em teste | Médio | rodar evals com o provider após validar o fallback | Agente |
| R-05 | Rate limit em memória; 1 conexão de polling por stream | Médio em escala | Redis/gateway; LISTEN/NOTIFY | Plataforma |
| R-06 | Sem scan de segredos/dependências no CI | Médio | gitleaks e pip-audit | Plataforma |
| R-07 | Login de demo concede privilégios reais | Alto se exposto | só local (`DEMO_LOGIN=1` via `start.ps1`); nunca em produção | Plataforma |
| R-08 | Sem verificação em navegador real; bundle ~870 kB | Baixo | E2E e code-splitting | Frontend |
| R-09 | Dados e métricas sintéticos | — | manter o aviso "simulado" em toda tela e resposta | Todos |

## Antes de produção
- [ ] `DEMO_LOGIN` ausente/0 e `JWT_SECRET` forte e rotacionado
- [ ] Fontes oficiais ingeridas e revisadas (R-02)
- [ ] Evals e `tests/test_redteam.py` verdes com o provider real
- [ ] Rate limit distribuído e scan de segredos no CI
- [ ] Revisão jurídica/LGPD do uso de dados reais
