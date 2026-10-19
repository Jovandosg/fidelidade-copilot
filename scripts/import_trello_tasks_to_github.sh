#!/usr/bin/env bash
# Importa os 11 cartões atuais do Trello Hacka Avanade como GitHub Issues.
# Não pede nem expõe senhas ou tokens. A autenticação é feita pelo gh CLI.
set -Eeuo pipefail

REPO="${REPO:-Jovandosg/fidelidade-copilot}"
PROJECT_NUMBER="${PROJECT_NUMBER:-}"
OWNER="${OWNER:-Jovandosg}"

fail() { echo "ERRO: $*" >&2; exit 1; }
command -v gh >/dev/null 2>&1 || fail "Instale o GitHub CLI (gh)."
gh auth status >/dev/null 2>&1 || fail "Autentique-se com gh auth login."
gh repo view "$REPO" --json nameWithOwner,viewerPermission >/dev/null 2>&1 || fail "A conta não consegue acessar $REPO."

label() {
  gh label create "$1" --repo "$REPO" --color "$2" --description "$3" --force >/dev/null 2>&1 || true
}

label "trello-sync" "0E8A16" "Importado do quadro Hacka Avanade"
label "dados" "1D76DB" "Frente de dados"
label "ml-valor" "5319E7" "Frente de ML e valor"
label "agente" "D93F0B" "Frente de agente"
label "dashboard" "FBCA04" "Frente de dashboard"
label "produto-pitch" "C5DEF5" "Frente de produto e pitch"
label "integracao" "B60205" "Integração e release"
label "trello-done" "0E8A16" "Cartão concluído no Trello"
label "trello-doing" "FBCA04" "Cartão em andamento no Trello"

create_issue() {
  local title="$1" labels="$2" body="$3"
  if gh issue list --repo "$REPO" --state all --search "in:title $title" --json title --jq '.[].title' | grep -Fxq "$title"; then
    echo "Já existe: $title"
    return 0
  fi
  local url
  url="$(gh issue create --repo "$REPO" --title "$title" --body "$body" --label "$labels")"
  echo "Criada: $url"
  if [[ -n "$PROJECT_NUMBER" ]]; then
    gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$url" >/dev/null 2>&1 || \
      echo "AVISO: Issue criada, mas não adicionada ao Project: $title" >&2
  fi
}

create_issue "P1 | Pipeline raw → treated → analytics" "trello-sync,dados,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/jmTF5Aqj/2-p1-pipeline-raw-%E2%86%92-treated-%E2%86%92-analytics
- Lista: Pessoa 1 — Dados
- Responsável: Pessoa 1 — Dados
- Revisor: Pessoa 2 — ML e Valor
- Prazo no Trello: 20/10/2026

## Objetivo
Construir e congelar o pipeline de execução do MVP.

## Entregas
- Transformações raw → treated → analytics.
- Features versionadas e tabela customer_features.
- Campos de rota, preferência, relacionamento, experiência e influência.
- Logs de execução e comando único de execução.
- Teste em ambiente limpo e README de reprodutibilidade.

## Critérios de aceite
- Execução idempotente.
- Dados analíticos consumidos por ML, agente e dashboard.
- Nenhum segredo ou dado real no repositório.
- Marco de 20/10 com fluxo ponta a ponta possível.

## Status de origem
Cartão aberto no Trello.
BODY
)"

create_issue "P2 | Score, CLV, churn e segmentos" "trello-sync,ml-valor,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/yZJVdNsl/3-p2-score-clv-churn-e-segmentos
- Lista: Pessoa 2 — ML e Valor
- Responsável: Pessoa 2 — ML e Valor
- Revisor: Pessoa 1 — Dados
- Prazo no Trello: 17/10/2026

## Objetivo
Implementar o núcleo analítico do copiloto.

## Entregas
- Score de alto valor com pesos documentados.
- Estimativa de CLV.
- Modelo baseline de churn.
- Quatro segmentos: Premium recorrente; Corporativo em risco; Lazer de alto potencial; Influenciador de experiência.
- Métricas, thresholds, explicabilidade e limitações.

## Critérios de aceite
- Scores entre 0 e 100.
- Risco entre 0 e 1.
- Segmentação reproduzível.
- Explicações disponíveis por cliente.
- Não depender apenas de gasto acumulado.

## Status de origem
Cartão aberto no Trello.
BODY
)"

create_issue "P2 | Validação, fairness e números finais" "trello-sync,ml-valor,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/4xweIyRv/4-p2-valida%C3%A7%C3%A3o-fairness-e-n%C3%BAmeros-finais
- Lista: Pessoa 2 — ML e Valor
- Responsável: Pessoa 2 — ML e Valor
- Revisor: Pessoa 1 — Dados
- Prazo no Trello: 23/10/2026

## Entregas
- Testes de qualidade e estabilidade das distribuições sintéticas.
- Validação de métricas e revisão de thresholds.
- Registro de limitações, vieses e riscos de interpretação.
- Números finais para o caso demonstrado.
- Auditoria das métricas em 25/10.

## Critérios de aceite
- Métricas reproduzíveis.
- Limitações visíveis no produto/documentação.
- Nenhum resultado apresentado como evidência de dados reais.
- Pessoa 5 recebe os números finais até 23/10.

## Status de origem
Cartão aberto no Trello.
BODY
)"

create_issue "P3 | Agente, ferramentas e contrato JSON" "trello-sync,agente,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/MQEh87vx/5-p3-agente-ferramentas-e-contrato-json
- Lista: Pessoa 3 — Agente
- Responsável: Pessoa 3 — Agente
- Revisor: Pessoa 4 — Dashboard
- Prazo no Trello: 20/10/2026

## Entregas
- Agente com escopo fechado e saída estruturada.
- Ferramentas permitidas para perfil, score, evidências, ações elegíveis, parceiros, validação e aprovação.
- Catálogo de ações/parceiros com elegibilidade, custo, margem, rota e validade.
- Contrato Pydantic/JSON Schema para recommendation.
- Integração do agente ao MVP.

## Critérios de aceite
- Agente não consulta tabelas arbitrárias nem executa ações externas.
- Toda recomendação contém evidências, confiança, flags e requires_human_approval.
- Fallback por regras funciona sem LLM.

## Status de origem
Cartão aberto no Trello.
BODY
)"

create_issue "P3 | Guardrails, prompt injection e fallback" "trello-sync,agente,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/ZAJmLbzn/6-p3-guardrails-prompt-injection-e-fallback
- Lista: Pessoa 3 — Agente
- Responsável: Pessoa 3 — Agente
- Revisor: Pessoa 4 — Dashboard
- Prazo no Trello: 23/10/2026

## Entregas
- Testes contra prompt injection e ação fora da política.
- Fallback determinístico quando o LLM falhar.
- Logs sem segredos.
- Avisos sobre dados sintéticos, parceiros e aprovação humana.
- Fluxo final documentado e auditado em 25/10.

## Critérios de aceite
- Recomendação inválida é bloqueada.
- Dashboard continua funcionando sem LLM.
- Logs permitem rastrear a decisão.
- Limitações de IA aparecem na demonstração.

## Status de origem
Cartão aberto no Trello.
BODY
)"

create_issue "P4 | Dashboard Streamlit e fluxo de priorização" "trello-sync,dashboard,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/Z7SjFEEu/7-p4-dashboard-streamlit-e-fluxo-de-prioriza%C3%A7%C3%A3o
- Lista: Pessoa 4 — Dashboard
- Responsável: Pessoa 4 — Dashboard
- Revisor: Pessoa 5 — Produto e Pitch
- Prazo no Trello: 17/10/2026

## Entregas
- Filtros por segmento, risco, prioridade, rota e nível.
- Tabela de clientes e perfil detalhado.
- Gráficos de score versus risco, CLV e segmentos.
- Evidências e explicações do score.
- Wireframe convertido em telas funcionais.

## Critérios de aceite
- Usuário encontra o caso corporativo em risco em poucos passos.
- Informações são legíveis.
- Interface funciona com dados sintéticos.
- Botão e estados de carregamento previstos para a recomendação.

## Status de origem
Cartão aberto no Trello.
BODY
)"

create_issue "P4 | Integração, usabilidade e teste da demo" "trello-sync,dashboard,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/1XWR1C96/8-p4-integra%C3%A7%C3%A3o-usabilidade-e-teste-da-demo
- Lista: Pessoa 4 — Dashboard
- Responsável: Pessoa 4 — Dashboard
- Revisor: Pessoa 5 — Produto e Pitch
- Prazo no Trello: 25/10/2026

## Entregas
- Botão Gerar próxima melhor ação.
- Renderização da recomendação, parceiro, evidências, confiança, custo/limite e aprovação humana.
- Fallback visual.
- Teste de usabilidade e correções.
- Screenshots finais e ensaio da demo em 25/10.

## Critérios de aceite
- Fluxo ponta a ponta funciona.
- Demo é reproduzível.
- Não há promessa de parceria.
- Aprovação humana fica explícita.
- Dashboard permanece operacional em ambiente limpo.

## Status de origem
Cartão aberto no Trello.
BODY
)"

create_issue "P5 | Produto, benchmark e hipóteses de parceria" "trello-sync,produto-pitch,trello-done" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/GVKDYRq2/9-p5-produto-benchmark-e-hip%C3%B3teses-de-parceria
- Lista: Pessoa 5 — Produto e Pitch
- Responsável: Pessoa 5 — Produto e Pitch
- Revisor: Pessoa 3 — Agente
- Prazo no Trello: 17/10/2026
- Status no Trello: Done

## Entregas
- Hipótese de negócio e problema de CRM.
- Benchmark Azul × LATAM Pass × Smiles sem alegar superioridade absoluta.
- Catálogo de hipóteses de parceria.
- Jornada e métricas de sucesso.
- Critérios para seleção de parceiro.

## Critérios de aceite
- Ofertas marcadas como sujeitas a contrato, estoque e elegibilidade.
- Produto responde quem priorizar, por quê, qual ação e como medir.
- Backlog priorizado para a demo.
BODY
)"

create_issue "P5 | Pitch de 5 minutos, README e submissão" "trello-sync,produto-pitch,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/r7iWk5FP/10-p5-pitch-de-5-minutos-readme-e-submiss%C3%A3o
- Lista: Pessoa 5 — Produto e Pitch
- Responsável: Pessoa 5 — Produto e Pitch
- Revisor: Pessoa 3 — Agente
- Prazo no Trello: 26/10/2026

## Entregas
- Roteiro com problema, solução, alto valor, caso em risco, diferencial, parcerias, tecnologia, segurança e impacto.
- Vídeo de pitch de até 5 minutos e ensaios.
- README, arquitetura, metodologia, dicionário, políticas e IA responsável.
- Conferência de números, restrições, links e repositório privado.
- Auditoria final em 25/10 e submissão em 26/10.

## Critérios de aceite
- Demonstração de um único caso principal.
- Stack e limitações explicadas.
- Checklist final completo.
- Vídeo dentro do limite.
- Todos os links funcionais.

## Status de origem
Cartão aberto no Trello.
BODY
)"

create_issue "Integração, revisão cruzada e release" "trello-sync,integracao,trello-doing" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/zTmOrLOt/11-integra%C3%A7%C3%A3o-revis%C3%A3o-cruzada-e-release
- Lista: Integração
- Coordenadora: Pessoa 5 — Produto e Pitch
- Participação: todas as pessoas
- Prazo no Trello: 26/10/2026

## Marcos
- 11/10: escopo e contratos congelados.
- 14/10: dados reproduzíveis e baseline funcionando.
- 17/10: segmentos e catálogo de ações definidos.
- 20/10: fluxo ponta a ponta funcionando.
- 23/10: conteúdo final e limitações aprovados.
- 25/10: release candidata, auditorias e ensaio.
- 26/10: última verificação e submissão.

## Checklist de integração
- Dados analíticos consumidos por ML, agente e dashboard.
- Contrato JSON validado e renderizado no dashboard.
- Human-in-the-loop visível.
- Parceiros apresentados como hipóteses.
- Testes de política, prompt injection, usabilidade e ambiente limpo executados.
- README, links e repositório privado conferidos.

## Status de origem
Cartão aberto no Trello.
BODY
)"

# Cartão concluído de dados: importar como histórico para rastreabilidade.
create_issue "P1 - Jovando | Dados reproduzíveis e contratos" "trello-sync,dados,trello-done" "$(cat <<'BODY'
## Origem
- Trello: https://trello.com/c/IpelZJ0C/1-p1-jovando-dados-reproduz%C3%ADveis-e-contratos
- Lista: Done
- Responsável: Pessoa 1 — Dados
- Revisor: Pessoa 2 — ML e Valor
- Prazo no Trello: 14/10/2026
- Status no Trello: Done

## Entregas
- Estrutura data/raw, data/treated e data/analytics.
- Gerador sintético com semente fixa e 1.200 clientes.
- Contratos de dados e dicionário de campos.
- Validações de esquema, nulos, duplicidades e valores impossíveis.
- Fontes públicas e metadados documentados.

## Critérios de aceite
- Pipeline reproduzível.
- Camadas separadas.
- Base substituível por dados reais sem reconstruir a aplicação.
- Validações executáveis em ambiente limpo.

## Status de origem
Cartão concluído no Trello; Issue criada para histórico e rastreabilidade.
BODY
)"

echo "Sincronização concluída."
if [[ -n "$PROJECT_NUMBER" ]]; then
  echo "As Issues foram adicionadas ao Project ${PROJECT_NUMBER}; ajuste manualmente os status para To Do, In Progress, In Review e Done conforme o Trello."
else
  echo "Para adicionar ao Project, execute com PROJECT_NUMBER=<numero> e uma conta que possa editar o Project."
fi
