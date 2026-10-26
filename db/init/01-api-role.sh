#!/bin/sh
# Executado pelo container na primeira inicializacao: cria o login somente leitura da API.
# A senha vem do ambiente (.env), nunca do repositorio.
set -e
psql -v ON_ERROR_STOP=1 -v pw="$POSTGRES_API_PASSWORD" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
CREATE ROLE fidelidade_ro LOGIN PASSWORD :'pw';
EOSQL
