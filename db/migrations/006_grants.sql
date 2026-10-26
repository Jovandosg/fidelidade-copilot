-- 006: permissoes por papel (menor privilegio). Reexecutavel: GRANT/REVOKE sao idempotentes.
-- etl: grava raw/treated/analytics e ops de pipeline; nao toca no audit_log.
-- api_ro: somente SELECT em analytics e ops (exceto audit_log).
-- api_audit: INSERT e SELECT apenas em ops.audit_log (leitura da propria trilha para o auditor).

GRANT USAGE ON SCHEMA raw, treated, analytics, ops TO fidelidade_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA raw, treated, analytics TO fidelidade_etl;
GRANT SELECT, INSERT, UPDATE ON ops.pipeline_runs, ops.data_quality_results, ops.model_registry, ops.drift_metrics TO fidelidade_etl;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ops TO fidelidade_etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fidelidade_etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA treated GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fidelidade_etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fidelidade_etl;

GRANT USAGE ON SCHEMA ops TO fidelidade_ro;
GRANT SELECT ON ops.pipeline_runs, ops.data_quality_results, ops.model_registry, ops.drift_metrics TO fidelidade_ro;

GRANT USAGE ON SCHEMA ops TO fidelidade_api_audit;
GRANT USAGE ON SCHEMA analytics TO fidelidade_api_audit;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO fidelidade_api_audit;
GRANT SELECT, INSERT ON ops.audit_log TO fidelidade_api_audit;
GRANT USAGE ON SEQUENCE ops.audit_log_id_seq TO fidelidade_api_audit;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO fidelidade_api_audit;

REVOKE UPDATE, DELETE, TRUNCATE ON ops.audit_log FROM PUBLIC, fidelidade_ro, fidelidade_etl, fidelidade_api_audit;
