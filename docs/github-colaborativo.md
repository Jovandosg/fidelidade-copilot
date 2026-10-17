# Ambiente colaborativo no GitHub

## Limitação atual

A configuração desta documentação foi preparada no repositório local. A conta GitHub disponível na sessão de preparação não conseguiu visualizar o repositório `Jovandosg/fidelidade-copilot`, portanto Issues, membros e Project não puderam ser criados automaticamente nesta sessão.

Alternativa simples: um proprietário ou colaborador com permissão de escrita deve executar o script `scripts/setup_github_collaboration.sh` após autenticar o GitHub CLI. Se o comando de Projects não estiver disponível, crie o quadro pela interface web seguindo o roteiro abaixo.

## Passo 1 — Confirmar a conta

```bash
gh auth status
gh repo view Jovandosg/fidelidade-copilot --json nameWithOwner,viewerPermission,url
```

A conta deve aparecer como membro do repositório e possuir permissão `WRITE`, `MAINTAIN` ou `ADMIN`.

## Passo 2 — Testar acesso dos integrantes

Cada integrante deve aceitar o convite do repositório e confirmar no navegador que consegue abrir o projeto.

Teste sem alterar código:

```bash
git ls-remote https://github.com/Jovandosg/fidelidade-copilot.git
```

Teste de escrita controlado:

1. criar uma branch;
2. alterar uma linha de documentação;
3. abrir um Pull Request;
4. pedir revisão;
5. fazer merge somente com autorização do fluxo do time;
6. excluir a branch após o merge.

Os integrantes não devem compartilhar senhas, tokens ou credenciais. O avaliador autorizado deve receber somente o nível de acesso necessário para leitura, revisão ou avaliação.

## Passo 3 — Regras básicas

- `main` representa a versão integrada e demonstrável.
- Não fazer push direto em `main`, salvo correção urgente acordada.
- Usar branches curtas: `feature/us-01-priorizacao`, `fix/us-04-risco`, `docs/missao-05`.
- Abrir Pull Request para mudanças relevantes.
- Uma pessoa diferente do autor revisa o Pull Request quando possível.
- Commits pequenos e objetivos, no imperativo: `Add customer priority view`.
- Não enviar `.env`, tokens, senhas, dados reais ou arquivos confidenciais.
- Executar os testes pertinentes antes de pedir revisão.
- Resolver conflitos localmente e explicar decisões no Pull Request.

## Onde registrar cada coisa

| Item | Local recomendado |
|---|---|
| User Stories | GitHub Issues usando o template `User Story` |
| Critérios de aceitação | Corpo da Issue da User Story |
| Tasks técnicas | Issues vinculadas à User Story, usando o template `Task técnica` |
| Impedimentos | Issue usando o template `Impedimento` e comentário no cartão afetado |
| Visão do produto | `docs/visao-produto.md` e Issue de decisão quando houver mudança |
| Product Goal | `docs/visao-produto.md` e Issue fixada ou marcada como decisão |
| Definition of Done | `docs/definition-of-done.md` |
| Sprint 01 | `docs/sprints/sprint-01.md` |
| Discussão de implementação | Pull Request |
| Decisões importantes | Issue ou Pull Request com seção “Decisão” |
| Feedback da Sprint Review | `docs/sprints/sprint-01.md` |
| Retrospective | `docs/sprints/sprint-01.md` |

## Passo 4 — Criar o Project

Pela interface do GitHub:

1. Acesse o repositório.
2. Abra **Projects**.
3. Selecione **New project** e escolha um quadro vazio.
4. Nomeie como `Hacka Avanade — Sprint 01`.
5. Mantenha as colunas/status:
   - `To Do`;
   - `In Progress`;
   - `In Review`;
   - `Done`.
6. Adicione as Issues do repositório ao quadro.
7. Ordene as User Stories pela decisão da Product Owner.
8. Use `In Review` apenas quando os critérios de aceitação estiverem implementados e aguardarem revisão.

Se o GitHub oferecer apenas `Todo`, `In Progress` e `Done`, crie uma opção `In Review` no campo de status ou use uma segunda visualização filtrada por uma label `in-review`.

## Passo 5 — Convidar avaliadores

- Use **Settings → Collaborators**.
- Conceda a menor permissão necessária.
- Para avaliação sem alteração de código, prefira leitura.
- Para revisão de Pull Requests, use a permissão disponível mais restrita que permita revisar.
- Remova acessos temporários após o hackathon.

## Passo 6 — Verificação final

```bash
gh issue list --repo Jovandosg/fidelidade-copilot
gh project list --owner Jovandosg
git status
git branch -a
```

O ambiente estará pronto quando os integrantes conseguirem abrir Issues, criar branches, abrir Pull Requests, revisar mudanças e visualizar o quadro sem compartilhar credenciais.
