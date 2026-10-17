#!/usr/bin/env bash
# Cria labels, Issues e um Project inicial para o Hacka Avanade.
# Execute com uma conta que tenha permissão de escrita no repositório.
set -Eeuo pipefail

REPO="${REPO:-Jovandosg/fidelidade-copilot}"
OWNER="${OWNER:-Jovandosg}"
PROJECT_TITLE="${PROJECT_TITLE:-Hacka Avanade — Sprint 01}"

fail() { echo "ERRO: $*" >&2; exit 1; }
command -v gh >/dev/null || fail "Instale o GitHub CLI (gh)."
gh auth status >/dev/null 2>&1 || fail "Execute gh auth login antes de continuar."
gh repo view "$REPO" --json viewerPermission >/dev/null 2>&1 || fail "A conta não consegue acessar $REPO."

create_label() {
  local name="$1" color="$2" description="$3"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$description" --force >/dev/null 2>&1 || true
}

create_label "user story" "1D76DB" "Necessidade de usuário com valor e critérios"
create_label "task" "5319E7" "Tarefa técnica ligada a uma User Story"
create_label "impedimento" "B60205" "Bloqueio que impede o avanço"
create_label "in-review" "FBCA04" "Aguardando revisão"
create_label "sprint-01" "0E8A16" "Trabalho do Sprint 01"

create_issue() {
  local title="$1" body="$2" labels="$3"
  if gh issue list --repo "$REPO" --state all --search "in:title $title" --json title --jq '.[].title' | grep -Fxq "$title"; then
    echo "Issue já existe: $title"
  else
    gh issue create --repo "$REPO" --title "$title" --body "$body" --label "$labels"
  fi
}

create_issue "US-01 Priorizar clientes estratégicos" $'Como profissional de CRM, quero visualizar uma lista priorizada de clientes estratégicos, para decidir quem merece atenção primeiro.\n\nCritérios de aceitação:\n- lista com prioridade e identificador;\n- caso corporativo em risco localizável;\n- regra de ordenação compreensível.\n\nDefinition of Done: ver docs/definition-of-done.md.' "user story,sprint-01"
create_issue "US-02 Compreender evidências da prioridade" $'Como profissional de CRM, quero entender as evidências da prioridade, para tomar uma decisão explicável.\n\nCritérios de aceitação:\n- pelo menos duas evidências;\n- linguagem compreensível;\n- limitações visíveis.' "user story,sprint-01"
create_issue "US-03 Visualizar perfil contextual" $'Como profissional de CRM, quero consultar o perfil contextual, para avaliar a jornada antes de considerar uma ação.\n\nCritérios de aceitação:\n- valor, comportamento, potencial e relacionamento disponíveis;\n- rota ou preferência quando disponível;\n- dados sintéticos identificados.' "user story,sprint-01"
create_issue "US-04 Identificar risco de evasão" $'Como profissional de CRM, quero identificar clientes estratégicos com sinais de risco, para agir antes da perda de preferência.\n\nCritérios de aceitação:\n- risco conforme limite definido;\n- caso principal identificável;\n- resultado apresentado como estimativa, não certeza real.' "user story,sprint-01"
create_issue "US-05 Diferenciar segmentos" $'Como profissional de CRM, quero visualizar segmentos de clientes, para evitar uma ação igual para todos.\n\nCritérios de aceitação:\n- segmentos definidos pela equipe;\n- objetivo de cada segmento;\n- segmento do caso principal visível.' "user story,sprint-01"
create_issue "US-06 Recomendar próxima melhor ação" $'Como profissional de CRM, quero receber uma ação contextual, para avaliar uma resposta de retenção ou desenvolvimento.\n\nCritérios de aceitação:\n- ação relacionada ao contexto;\n- evidências e limites;\n- aprovação humana;\n- nenhuma oferta inventada quando não elegível.' "user story,sprint-01"
create_issue "US-07 Avaliar hipótese de parceiro" $'Como profissional de CRM, quero consultar uma hipótese de parceiro ou experiência, para avaliar uma jornada relevante.\n\nCritérios de aceitação:\n- relação com rota/segmento;\n- hipótese claramente identificada;\n- aviso de contrato, estoque e elegibilidade.' "user story,sprint-01"
create_issue "US-08 Revisar recomendação antes da ativação" $'Como responsável pela aprovação, quero revisar uma recomendação, para manter controle humano.\n\nCritérios de aceitação:\n- estado de aprovação visível;\n- nenhuma ativação automática;\n- resultado da revisão demonstrável.' "user story,sprint-01"
create_issue "US-09 Continuar com fallback baseado em regras" $'Como integrante da equipe que demonstra o produto, quero um fallback quando a geração inteligente falhar, para não interromper a demonstração.\n\nCritérios de aceitação:\n- falha identificada;\n- alternativa baseada em regras;\n- usuário avisado;\n- evidências e aprovação preservadas.' "user story,sprint-01"
create_issue "US-10 Demonstrar fluxo completo" $'Como avaliador do hackathon, quero acompanhar um caso desde os sinais até a recomendação, para entender valor e limites.\n\nCritérios de aceitação:\n- caso principal executável;\n- prioridade, evidências, risco, ação e aprovação;\n- dados sintéticos e hipóteses identificados;\n- fluxo explicável em até cinco minutos.' "user story,sprint-01"

# Project: criação é suportada pelo gh quando a conta tem escopo project.
if gh project list --owner "$OWNER" --format json | grep -Fq "$PROJECT_TITLE"; then
  echo "Project já existe: $PROJECT_TITLE"
else
  gh project create --owner "$OWNER" --title "$PROJECT_TITLE" --format json || {
    echo "AVISO: não foi possível criar o Project por falta de escopo/permissão."
    echo "Alternativa: crie-o pela interface e configure os status To Do, In Progress, In Review e Done."
  }
fi

echo
 echo "Issues e labels configuradas."
echo "Abra o Project e adicione as Issues; mantenha os status: To Do, In Progress, In Review e Done."
