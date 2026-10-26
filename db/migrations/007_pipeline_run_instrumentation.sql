-- 007: instrumentacao do pipeline. Mensagem de erro por execucao e unicidade por regra (carga idempotente por run_id).
ALTER TABLE ops.pipeline_runs ADD COLUMN IF NOT EXISTS error text;
CREATE UNIQUE INDEX IF NOT EXISTS dq_results_run_rule_uidx ON ops.data_quality_results (run_id, entity, rule);
CREATE INDEX IF NOT EXISTS pipeline_runs_started_idx ON ops.pipeline_runs (started_at DESC);
