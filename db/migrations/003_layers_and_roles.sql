-- 003: camadas raw / treated / ops e papeis de menor privilegio.
-- Logins (com senha) sao criados fora do repo em db/init/01-api-role.sh; aqui so os papeis (NOLOGIN) quando ausentes.
-- fidelidade_etl: escreve raw/treated/analytics e ops de pipeline. fidelidade_ro: so SELECT. fidelidade_api_audit: so INSERT/SELECT no audit_log.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS treated;
CREATE SCHEMA IF NOT EXISTS ops;

DO $$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['fidelidade_ro', 'fidelidade_etl', 'fidelidade_api_audit'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', r);
        END IF;
    END LOOP;
END
$$;

REVOKE ALL ON SCHEMA raw, treated, ops FROM PUBLIC;
