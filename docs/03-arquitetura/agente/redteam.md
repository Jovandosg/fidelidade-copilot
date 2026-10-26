# Red team básico do agente

Executável: `python -m pytest tests/test_redteam.py -q` (testes de banco exigem `DATABASE_URL`, `_ETL`, `_RO` e `_AUDIT`; sem eles são pulados).

| # | Ataque | Controle | Teste |
|---|---|---|---|
| 1 | Injeção direta PT/EN, markup de papel, SQLi, pedido de ativação, zero-width, fullwidth, espaçamento | `check_input` bloqueia antes de qualquer ferramenta; recusa; nenhuma proposta criada | `test_direct_injection_*`, `test_api_blocks_injection_*` |
| 2 | Falso positivo em perguntas legítimas | corpus legítimo precisa passar | `test_legitimate_questions_*` |
| 3 | PII na pergunta | redigida antes do agente/log | `test_pii_in_question_*` |
| 4 | Fonte falsa: `voeazul.com.br.evil.com`, `notvoeazul.com.br`, userinfo, path, http, `javascript:` | host exato ou subdomínio, https | `test_citation_from_untrusted_host_*` |
| 5 | LLM malicioso: afirma ativação, PII, valor fora da fonte, citação inexistente | `check_output` → fallback por regras | `test_malicious_model_output_*`, `test_malicious_llm_output_falls_back_to_rules` |
| 6 | Ação divergente da elegibilidade; `requires_approval=false`; campos extras | schema estrito + conferência com a ferramenta | `test_proposed_action_*`, `test_requires_approval_*` |
| 7 | Abuso de ferramentas: inexistente, args extras, SQLi/path traversal, query enorme | `Toolbox` valida schema antes do banco | `test_toolbox_*` |
| 8 | JWT forjado, expirado, `alg=none`, papel inexistente, payload adulterado, TTL > 24 h | HS256 + issuer + papel + exp; 401 antes do banco | `test_forged_credentials_*`, `test_role_in_a_tampered_payload_*` |
| 9 | Autoaprovação, escalada de papel e dupla decisão concorrente | RBAC; trigger só permite pending→decidido | `test_double_decision_*` |
| 10 | 6 propostas simultâneas para o mesmo cliente | índice único de pendente: 1×200 e 5×409 | `test_concurrent_proposals_*` |
| 11 | Adulterar proposta/trilha mesmo com credencial do banco | triggers + GRANTs mínimos | `test_database_roles_block_tampering_*` |
| 12 | Vazamento da chave do LLM (inclusive eco do upstream) | sem log de corpo/cabeçalho; chave fora da resposta | `test_llm_key_never_leaks_*` |
| 13 | XSS/SQLi em texto, IDs hostis, corpo gigante/malformado | validação 422, `nosniff`, nada refletido | `test_hostile_*`, `test_oversized_*` |

## Resultado
- **Brecha encontrada e corrigida:** a checagem de fonte usava `endswith("voeazul.com.br")` e aceitava `notvoeazul.com.br`. Agora exige host exato ou subdomínio (`_trusted_host`).
- **Lacuna conhecida (xfail estrito):** injeção por paráfrase sem palavras-chave não é detectada por regex ([riscos.md](riscos.md) R-01). Se passar a ser detectada, o `xfail` falha e avisa.
- Suíte completa com banco temporário pgvector: 373 passaram, 1 xfail.
