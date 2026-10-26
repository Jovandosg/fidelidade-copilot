-- 002: papel somente leitura para a API. Senha/LOGIN sao definidos fora do repo (db/init/01-api-role.sh).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fidelidade_ro') THEN
        CREATE ROLE fidelidade_ro NOLOGIN;
    END IF;
END
$$;

REVOKE ALL ON SCHEMA analytics FROM PUBLIC;
GRANT USAGE ON SCHEMA analytics TO fidelidade_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO fidelidade_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO fidelidade_ro;
