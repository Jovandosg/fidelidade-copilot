-- 005: observabilidade da plataforma (schema ops). Preenchidas pelo pipeline (Tasks 3-4) e pela API (Task 5).
-- Metricas de modelo valem apenas para dados sinteticos (campo synthetic_notice).

CREATE TABLE IF NOT EXISTS ops.pipeline_runs (
    run_id           uuid         PRIMARY KEY,
    started_at       timestamptz  NOT NULL,
    finished_at      timestamptz,
    duration_ms      integer      CHECK (duration_ms >= 0),
    status           text         NOT NULL CHECK (status IN ('running', 'passed', 'failed')),
    code_version     text         NOT NULL,
    seed             integer      NOT NULL,
    contract_version text         NOT NULL,
    rows_by_entity   jsonb        NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ops.data_quality_results (
    id           bigserial    PRIMARY KEY,
    run_id       uuid         NOT NULL REFERENCES ops.pipeline_runs (run_id),
    entity       text         NOT NULL,
    rule         text         NOT NULL,
    passed       boolean      NOT NULL,
    failed_rows  integer      NOT NULL DEFAULT 0 CHECK (failed_rows >= 0),
    detail       jsonb,
    checked_at   timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dq_results_run_idx ON ops.data_quality_results (run_id);

CREATE TABLE IF NOT EXISTS ops.model_registry (
    id               bigserial    PRIMARY KEY,
    model_name       text         NOT NULL CHECK (model_name IN ('hvs', 'risk', 'nba')),
    model_version    text         NOT NULL,
    run_id           uuid         REFERENCES ops.pipeline_runs (run_id),
    trained_at       timestamptz  NOT NULL,
    data_hash        text         NOT NULL,
    metrics          jsonb        NOT NULL DEFAULT '{}'::jsonb,
    params           jsonb        NOT NULL DEFAULT '{}'::jsonb,
    synthetic_notice text         NOT NULL DEFAULT 'Metricas calculadas sobre dados sinteticos; nao representam desempenho real.',
    UNIQUE (model_name, model_version, data_hash)
);

CREATE TABLE IF NOT EXISTS ops.drift_metrics (
    id          bigserial     PRIMARY KEY,
    run_id      uuid          NOT NULL REFERENCES ops.pipeline_runs (run_id),
    feature     text          NOT NULL,
    psi         numeric(10,4) NOT NULL CHECK (psi >= 0),
    threshold   numeric(10,4) NOT NULL CHECK (threshold > 0),
    alert       boolean       NOT NULL,
    computed_at timestamptz   NOT NULL DEFAULT now(),
    UNIQUE (run_id, feature)
);

-- Trilha de auditoria append-only: sem UPDATE/DELETE/TRUNCATE (trigger + permissoes em 006).
CREATE TABLE IF NOT EXISTS ops.audit_log (
    id          bigserial    PRIMARY KEY,
    occurred_at timestamptz  NOT NULL DEFAULT now(),
    actor       text         NOT NULL,
    actor_role  text         NOT NULL CHECK (actor_role IN ('analista', 'gestor', 'auditor')),
    action      text         NOT NULL,
    entity      text         NOT NULL,
    entity_id   text         NOT NULL,
    before      jsonb,
    after       jsonb,
    request_id  text
);
CREATE INDEX IF NOT EXISTS audit_log_entity_idx ON ops.audit_log (entity, entity_id);

CREATE OR REPLACE FUNCTION ops.audit_log_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'ops.audit_log e append-only (% bloqueado)', TG_OP USING ERRCODE = 'insufficient_privilege';
END
$$;

DROP TRIGGER IF EXISTS audit_log_no_update_delete ON ops.audit_log;
CREATE TRIGGER audit_log_no_update_delete BEFORE UPDATE OR DELETE ON ops.audit_log
    FOR EACH ROW EXECUTE FUNCTION ops.audit_log_immutable();

DROP TRIGGER IF EXISTS audit_log_no_truncate ON ops.audit_log;
CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON ops.audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION ops.audit_log_immutable();
