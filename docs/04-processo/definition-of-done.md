# Missão 4 — Definition of Done e registros leves

## Contexto usado

Esta proposta considera o MVP **Azul CRM de Alto Valor** e o projeto `fidelidade-copilot`.

A base disponível indica:

- uso de dados sintéticos e fontes públicas apropriadas ao contexto do desafio;
- Python, pandas, NumPy, scikit-learn, Parquet, PostgreSQL, FastAPI, Plotly (legado), pytest; React 19, Vite, Tailwind, ApexCharts e vitest no front;
- score de valor, risco de evasão, segmentação, explicações e recomendação de próxima melhor ação;
- necessidade de aprovação humana;
- fallback baseado em regras quando a geração inteligente falhar;
- repositório privado;
- equipe iniciante, com tempo limitado de hackathon.

Os **recursos e limites não informados** — como ambiente oficial de deploy, credenciais de serviços, dados de produção, regras comerciais reais e cobertura de usuários — ficam fora desta DoD até serem confirmados pela equipe. A DoD não deve criar esses requisitos por conta própria.

---

## 1. O que é a Definition of Done

A **Definition of Done (DoD)** é o padrão comum de qualidade que toda entrega precisa cumprir para ser considerada concluída.

Ela responde:

> **A entrega está integrada, revisada, testada e suficientemente documentada para ser usada no Increment?**

A DoD vale para todas as User Stories que forem concluídas no Sprint, respeitando o tipo de entrega. Uma história não deve ser movida para **Concluído** apenas porque o código foi escrito.

### DoD não é a mesma coisa que critério de aceitação

| Item | Definition of Done | Critérios de aceitação |
|---|---|---|
| Abrangência | Padrão comum para todas as entregas | Condições específicas de uma User Story |
| Pergunta | A entrega tem qualidade suficiente? | A história faz o que o usuário precisa? |
| Exemplo | Foi revisada, testada e documentada | O usuário consegue ver a evidência da prioridade |
| Aplicação | Reutilizada em todas as histórias | Escrita novamente para cada história |

Uma User Story só está pronta quando atende **seus critérios de aceitação** e também a **DoD**.

---

## 2. Definition of Done compartilhada

Uma entrega do Increment é considerada **Done** quando todos os itens aplicáveis abaixo foram verificados.

### A. Valor e critérios da User Story

- [ ] Os critérios de aceitação da User Story foram verificados.
- [ ] O comportamento esperado pode ser demonstrado ou observado.
- [ ] O Product Owner, ou uma pessoa indicada por ele, confirmou que a entrega atende ao objetivo da história.
- [ ] Nenhuma funcionalidade extra foi incluída sem registro de decisão.

### B. Integração

- [ ] A alteração está integrada à branch acordada do projeto.
- [ ] O fluxo principal continua executável depois da alteração.
- [ ] A entrega não depende de arquivos que ficaram apenas no computador de uma pessoa.
- [ ] Dados, código, configuração necessária e documentação mínima estão no local correto do repositório.
- [ ] Não há conflito conhecido aguardando resolução.

Para o MVP, integração significa que a alteração não quebra o fluxo relevante:

**dados sintéticos → análise/score → evidências → recomendação → revisão humana → dashboard.**

### C. Testes pertinentes

- [ ] Foi executado pelo menos o teste adequado ao tipo de mudança.
- [ ] Testes automatizados existentes continuam passando.
- [ ] Mudanças no pipeline verificam contrato, quantidade esperada, valores válidos ou outro comportamento relevante.
- [ ] Mudanças no dashboard foram verificadas manualmente no fluxo afetado.
- [ ] Mudanças em recomendação ou regras foram verificadas com pelo menos um caso positivo e um caso de limite ou inválido.
- [ ] Falhas conhecidas foram registradas no cartão, e não escondidas.

**Regra para iniciantes:** não é necessário testar tudo de forma sofisticada. É necessário testar o que pode quebrar o valor da história.

Exemplos:

- Alterou score: verificar intervalo, cálculo e um caso conhecido.
- Alterou filtro: verificar seleção, resultado vazio e combinação de filtros.
- Alterou recomendação: verificar evidência, elegibilidade e aprovação humana.
- Alterou pipeline: executar do início ao fim em ambiente limpo ou documentar claramente o que foi executado.

### D. Revisão

- [ ] Outra pessoa do time revisou a alteração.
- [ ] A revisão verificou comportamento, clareza e riscos básicos, não apenas estilo.
- [ ] Comentários relevantes foram resolvidos ou registrados.
- [ ] O responsável pelo cartão e o revisor estão identificados no Trello.
- [ ] A entrega não foi aprovada pelo próprio autor sem uma segunda verificação, quando houver outra pessoa disponível.

### E. Documentação mínima

- [ ] O cartão do Trello descreve o que foi entregue.
- [ ] O cartão registra limitações, dependências ou decisões importantes.
- [ ] O README ou documento apropriado foi atualizado quando o modo de executar ou entender o projeto mudou.
- [ ] Novos campos, regras, thresholds ou hipóteses importantes foram explicados.
- [ ] A instrução de execução permanece válida ou foi corrigida.

Não é necessário produzir uma ata longa para cada tarefa. A documentação mínima deve permitir que outra pessoa execute, revise ou demonstre a entrega.

### F. Defeitos críticos

- [ ] Não há defeito crítico conhecido que impeça o objetivo da User Story.
- [ ] Não há erro conhecido que faça o produto apresentar uma recomendação inválida como válida.
- [ ] Não há quebra conhecida do fluxo principal da demonstração.
- [ ] Defeitos menores não resolvidos estão registrados com impacto e próximo passo.

Um defeito crítico é, por exemplo:

- pipeline que não executa;
- dashboard que não abre o caso principal;
- score ou risco fora do contrato definido;
- recomendação sem evidência apresentada como decisão confiável;
- ação de parceiro apresentada como acordo confirmado;
- ausência do aviso de aprovação humana quando ela é necessária.

### G. Uso autorizado de dados

Estas verificações são pertinentes porque o MVP trabalha com dados de clientes e o desafio determina o uso de dados sintéticos e públicos:

- [ ] A entrega utiliza somente dados autorizados para o desafio.
- [ ] Não foram adicionados dados reais de clientes, credenciais, tokens ou informações confidenciais.
- [ ] Arquivos `.env`, chaves e segredos não foram enviados ao repositório.
- [ ] Dados sintéticos estão identificados como sintéticos.
- [ ] Fontes públicas utilizadas estão registradas quando aplicável.
- [ ] Resultados do MVP não são descritos como validação em produção.

### H. Segurança, revisão humana e governança

Estas verificações são incluídas porque o produto recomenda ações de CRM e usa inteligência artificial ou regras de recomendação:

- [ ] O produto não ativa automaticamente uma campanha, benefício ou parceria.
- [ ] A necessidade de aprovação humana aparece antes de uma eventual ativação.
- [ ] A recomendação mostra evidências ou o motivo disponível para sua geração.
- [ ] Ofertas de parceiros são apresentadas como hipóteses sujeitas a contrato, disponibilidade e elegibilidade.
- [ ] Entrada inválida, ação fora da política ou recomendação sem dados suficientes não é apresentada como recomendação confiável.
- [ ] Existe fallback baseado em regras ou uma mensagem clara de indisponibilidade.

Esses itens não são uma exigência genérica para qualquer software. São pertinentes aqui porque o próprio desafio prevê agente/recomendação, aprovação humana, parceiros e dados sintéticos.

---

## 3. Checklist curto para o cartão do Trello

Quando a equipe precisar de uma versão rápida, pode copiar este checklist para cada User Story:

```text
Definition of Done
[ ] Critérios de aceitação verificados
[ ] Integrado ao fluxo do projeto
[ ] Teste pertinente executado
[ ] Revisado por outra pessoa
[ ] Trello e documentação mínima atualizados
[ ] Sem defeito crítico conhecido
[ ] Dados autorizados; sem segredos ou dados reais
[ ] Aprovação humana e limitações visíveis quando aplicável
```

Os dois últimos itens devem ser marcados como **não aplicáveis** somente quando a entrega realmente não tocar em dados, recomendação ou governança. A justificativa deve ficar no cartão.

---

## 4. Critérios de aceitação versus DoD — exemplo

### User Story

> Como profissional de CRM, quero visualizar uma recomendação contextual para um cliente em risco, para avaliar uma ação de retenção.

### Critérios de aceitação desta história

- O cliente em risco pode ser selecionado.
- A recomendação aparece relacionada ao contexto do cliente.
- A recomendação apresenta evidências.
- A recomendação informa que requer aprovação humana.

### DoD aplicada à mesma história

- A história foi integrada ao fluxo do dashboard.
- O caso positivo e um caso sem recomendação foram testados.
- Outra pessoa revisou o comportamento.
- A documentação informa que a parceria é hipótese.
- Não há credenciais nem dados reais.
- Não existe defeito crítico conhecido.

Os critérios respondem **o que a história precisa fazer**. A DoD responde **se a entrega foi feita com o padrão mínimo de qualidade do time**.

---

## 5. O que não será exigido

Para manter a DoD adequada ao nível da equipe e ao prazo do hackathon, não serão exigidos:

- atas do Daily;
- burndown manual;
- cobertura de testes com percentual arbitrário;
- revisão formal extensa para cada alteração;
- documentação duplicada em vários lugares;
- infraestrutura de produção;
- dados reais para validar o protótipo;
- automação sofisticada sem relação com uma User Story;
- arquitetura mais complexa apenas para parecer completa.

A equipe deve manter evidências suficientes de qualidade, não produzir burocracia sem valor.

---

## 6. Modelo de Sprint Review — até cinco linhas

Copiar e preencher no cartão ou documento do Sprint Review:

```text
Incremento: [o que foi entregue e demonstrado]
Resultado: [qual comportamento ou valor ficou disponível]
Feedback: [o que Deyse/equipe/banca observou]
Decisões: [o que será mantido, alterado ou removido]
Próximo passo: [ação priorizada e responsável]
```

O registro deve falar sobre o incremento e o feedback. Não precisa reproduzir toda a conversa da reunião.

### Exemplo preenchido

```text
Incremento: priorização e perfil do cliente corporativo em risco.
Resultado: é possível ver score, risco, evidências e rota no dashboard.
Feedback: faltou destacar que os dados são sintéticos.
Decisões: incluir aviso na tela e manter um único caso principal.
Próximo passo: integrar recomendação com aprovação humana — Emily.
```

---

## 7. Modelo de Retrospective — até cinco linhas

Copiar e preencher ao final do ciclo:

```text
Problema: [o que dificultou o trabalho ou reduziu a qualidade]
Causa provável: [por que isso aconteceu]
Melhoria: [mudança concreta para o próximo ciclo]
Responsável: [quem ajudará a aplicar a mudança]
Verificação: [como saberemos se melhorou]
```

### Exemplo preenchido

```text
Problema: a integração foi iniciada perto do prazo final.
Causa provável: contratos de dados e interface foram definidos separadamente.
Melhoria: fazer uma integração vertical pequena no início de cada ciclo.
Responsável: Jovando facilita; João Arthur e Emily executam.
Verificação: o caso principal roda do dado ao dashboard antes do próximo marco.
```

---

## 8. Como aplicar a DoD no trabalho diário

1. No refinamento, o time define os critérios de aceitação da User Story.
2. Durante o desenvolvimento, o responsável atualiza o cartão e registra impedimentos.
3. Antes de pedir revisão, o responsável executa os testes pertinentes.
4. O revisor verifica a história e a DoD.
5. Se tudo estiver atendido, o cartão pode ir para **Concluído**.
6. Se algo faltar, o cartão permanece em revisão ou volta para andamento, com a pendência registrada.
7. Na Sprint Review, o time demonstra o Increment usando as evidências produzidas.
8. Na Retrospective, o time escolhe poucas melhorias concretas para o próximo ciclo.

## Resultado esperado da Missão 4

Ao concluir esta missão, todos devem entender que:

- uma história não está pronta somente porque foi codificada;
- os critérios de aceitação pertencem à história específica;
- a DoD é o padrão comum de qualidade do time;
- testes devem ser pertinentes ao risco da mudança;
- revisão, documentação mínima e integração fazem parte da entrega;
- dados autorizados, segurança, aprovação humana e transparência são relevantes para este produto;
- registros leves são suficientes para Review e Retrospective;
- Daily e burndown não precisam virar burocracia.
