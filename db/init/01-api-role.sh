#!/bin/sh
# Executado pelo container na primeira inicializacao: cria o login somente leitura da API.
# A senha vem do ambiente (.env), nunca do repositorio. Este arquivo DEVE usar finais de linha LF (veja .gitattributes).
set -e
psql -v ON_ERROR_STOP=1 -v pw="$POSTGRES_API_PASSWORD" -v pw_etl="$POSTGRES_ETL_PASSWORD" -v pw_audit="$POSTGRES_AUDIT_PASSWORD" \
    --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
CREATE ROLE fidelidade_ro LOGIN PASSWORD :'pw';
CREATE ROLE fidelidade_etl LOGIN PASSWORD :'pw_etl';
CREATE ROLE fidelidade_api_audit LOGIN PASSWORD :'pw_audit';
EOSQL
