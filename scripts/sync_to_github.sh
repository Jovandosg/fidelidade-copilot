#!/usr/bin/env bash
# Sincroniza um projeto local com um repositório GitHub sem sobrescrever o histórico remoto.
# Uso:
#   ./scripts/sync_to_github.sh
#   SOURCE_DIR=/caminho/projeto ./scripts/sync_to_github.sh
#   REPO_URL=https://github.com/usuario/repositorio.git BRANCH=main ./scripts/sync_to_github.sh

set -Eeuo pipefail

REPO_URL="${REPO_URL:-https://github.com/Jovandosg/fidelidade-copilot.git}"
BRANCH="${BRANCH:-main}"
SOURCE_DIR="${SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
WORK_DIR="${WORK_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/fidelidade-copilot-sync.XXXXXX")}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-chore: synchronize project files}"
KEEP_WORK_DIR="${KEEP_WORK_DIR:-0}"

cleanup() {
  if [[ "$KEEP_WORK_DIR" == "1" ]]; then
    printf 'Pasta temporária preservada em: %s\n' "$WORK_DIR"
  else
    rm -rf "$WORK_DIR"
  fi
}
trap cleanup EXIT

fail() {
  printf 'ERRO: %s\n' "$*" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "git não está instalado."
command -v gh >/dev/null 2>&1 || fail "GitHub CLI (gh) não está instalado."
[[ -d "$SOURCE_DIR" ]] || fail "SOURCE_DIR não existe: $SOURCE_DIR"
[[ -f "$SOURCE_DIR/README.md" || -f "$SOURCE_DIR/package.json" || -f "$SOURCE_DIR/pyproject.toml" || -f "$SOURCE_DIR/requirements.txt" ]] || \
  fail "SOURCE_DIR não parece ser a raiz de um projeto: $SOURCE_DIR"

printf '%s\n' '== 1/6. Validando autenticação GitHub =='
gh auth status >/dev/null 2>&1 || fail "Faça login antes: gh auth login --hostname github.com"
gh auth setup-git >/dev/null 2>&1 || fail "Não foi possível configurar o Git para usar o GitHub CLI."

printf '%s\n' '== 2/6. Verificando acesso ao repositório =='
gh repo view "$REPO_URL" --json nameWithOwner,viewerPermission >/dev/null 2>&1 || \
  fail "A conta autenticada não consegue acessar $REPO_URL. Verifique o acesso de escrita e o SSO."

printf '%s\n' '== 3/6. Clonando o repositório remoto =='
mkdir -p "$WORK_DIR"
CLONE_DIR="$WORK_DIR/repository"
git clone --origin origin "$REPO_URL" "$CLONE_DIR" >/dev/null 2>&1 || \
  fail "Não foi possível clonar o repositório. Verifique a URL e as permissões."
cd "$CLONE_DIR"

printf '%s\n' '== 4/6. Preparando a branch de destino =='
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git switch -c "$BRANCH" --track "origin/$BRANCH" >/dev/null 2>&1 || \
    git switch "$BRANCH" >/dev/null 2>&1 || fail "Não foi possível selecionar a branch $BRANCH."
else
  git switch --orphan "$BRANCH" >/dev/null 2>&1 || fail "Não foi possível criar a branch $BRANCH."
  git rm -rf . >/dev/null 2>&1 || true
fi

printf '%s\n' '== 5/6. Copiando arquivos do projeto =='
# rsync preserva permissões e permite excluir artefatos locais desnecessários.
# Sem --delete: arquivos já existentes no repositório remoto não são removidos.
command -v rsync >/dev/null 2>&1 || fail "rsync não está instalado."
rsync -a \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='node_modules/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='.DS_Store' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='*.log' \
  "$SOURCE_DIR/" "$CLONE_DIR/"

# Impede que um diretório .git acidental dentro de uma subpasta seja enviado.
find "$CLONE_DIR" -type d -name .git -not -path "$CLONE_DIR/.git" -prune -exec rm -rf {} + 2>/dev/null || true

git add --all
if git diff --cached --quiet; then
  printf '%s\n' 'Nenhuma alteração nova para enviar.'
  exit 0
fi

git commit -m "$COMMIT_MESSAGE" >/dev/null || fail "Não foi possível criar o commit."

printf '%s\n' '== 6/6. Enviando para o GitHub =='
git push --set-upstream origin "$BRANCH" || \
  fail "Push recusado. Confirme permissão Write, token, SSO e branch protegida."

printf '\nSincronização concluída com sucesso.\nRepositório: %s\nBranch: %s\nCommit: %s\n' \
  "$REPO_URL" "$BRANCH" "$(git rev-parse --short HEAD)"
