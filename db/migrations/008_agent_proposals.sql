-- 008: propostas do agente (Prompt C, Task 1). O agente apenas PROPOE; ativacao so apos decisao humana.
-- Sem FK para analytics.customer_features: o ETL recarrega essa tabela a cada execucao.
-- Decisoes tambem vao para ops.audit_log (append-only); aqui fica o estado corrente da proposta.

CREATE TABLE IF NOT EXISTS ops.agent_proposals (
    proposal_id         uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          timestamptz   NOT NULL DEFAULT now(),
    customer_id         text          NOT NULL CHECK (customer_id ~ '^C[0-9]{6}$'),
    action              text          NOT NULL CHECK (length(action) BETWEEN 1 AND 200),
    expected_margin_brl numeric(12,2) NOT NULL CHECK (expected_margin_brl >= 0),
    rationale           text          NOT NULL CHECK (length(rationale) BETWEEN 1 AND 2000),
    sources             jsonb         NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(sources) = 'array'),
    guardrails          jsonb         NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(guardrails) = 'object'),
    provider            text          NOT NULL CHECK (provider IN ('rules', 'llm')),
    simulated           boolean       NOT NULL DEFAULT true,
    status              text          NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    requested_by        text          NOT NULL,
    request_id          text,
    decided_by          text,
    decided_at          timestamptz,
    decision_reason     text,
    CHECK ((status = 'pending') = (decided_by IS NULL AND decided_at IS NULL)),
    CHECK (status = 'pending' OR decision_reason IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS agent_proposals_status_idx ON ops.agent_proposals (status, created_at DESC);
CREATE INDEX IF NOT EXISTS agent_proposals_customer_idx ON ops.agent_proposals (customer_id);
CREATE UNIQUE INDEX IF NOT EXISTS agent_proposals_one_pending_idx ON ops.agent_proposals (customer_id) WHERE status = 'pending';

-- Maquina de estados: so pending -> approved|rejected; conteudo da proposta e imutavel; sem DELETE/TRUNCATE.
CREATE OR REPLACE FUNCTION ops.agent_proposals_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP <> 'UPDATE' THEN
        RAISE EXCEPTION 'ops.agent_proposals nao permite % (use o audit_log)', TG_OP USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF OLD.status <> 'pending' THEN
        RAISE EXCEPTION 'proposta ja decidida (%)', OLD.status USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF (NEW.proposal_id, NEW.created_at, NEW.customer_id, NEW.action, NEW.expected_margin_brl, NEW.rationale, NEW.sources,
        NEW.guardrails, NEW.provider, NEW.simulated, NEW.requested_by, NEW.request_id)
       IS DISTINCT FROM
       (OLD.proposal_id, OLD.created_at, OLD.customer_id, OLD.action, OLD.expected_margin_brl, OLD.rationale, OLD.sources,
        OLD.guardrails, OLD.provider, OLD.simulated, OLD.requested_by, OLD.request_id) THEN
        RAISE EXCEPTION 'o conteudo da proposta e imutavel' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS agent_proposals_row_guard ON ops.agent_proposals;
CREATE TRIGGER agent_proposals_row_guard BEFORE UPDATE OR DELETE ON ops.agent_proposals
    FOR EACH ROW EXECUTE FUNCTION ops.agent_proposals_guard();

DROP TRIGGER IF EXISTS agent_proposals_no_truncate ON ops.agent_proposals;
CREATE TRIGGER agent_proposals_no_truncate BEFORE TRUNCATE ON ops.agent_proposals
    FOR EACH STATEMENT EXECUTE FUNCTION ops.agent_proposals_guard();

-- Menor privilegio: api_ro le; api_audit cria e decide (somente colunas de decisao); etl nao toca.
GRANT SELECT ON ops.agent_proposals TO fidelidade_ro;
GRANT SELECT, INSERT ON ops.agent_proposals TO fidelidade_api_audit;
GRANT UPDATE (status, decided_by, decided_at, decision_reason) ON ops.agent_proposals TO fidelidade_api_audit;
REVOKE DELETE, TRUNCATE ON ops.agent_proposals FROM PUBLIC, fidelidade_ro, fidelidade_etl, fidelidade_api_audit;
