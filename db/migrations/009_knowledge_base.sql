-- 009: base de conhecimento do RAG (Prompt C, Task 2). Requer a extensao pgvector (imagem pgvector/pgvector:pg16).
-- Somente regras PUBLICAS, com URL e data de consulta. Reingestao com conteudo novo cria nova versao (a anterior deixa de ser corrente).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.public_sources (
    source_id     bigserial    PRIMARY KEY,
    url           text         NOT NULL CHECK (url ~ '^https://'),
    title         text         NOT NULL,
    publisher     text         NOT NULL,
    consulted_at  date         NOT NULL,
    license_note  text,
    content_hash  text         NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    version       integer      NOT NULL CHECK (version >= 1),
    is_current    boolean      NOT NULL DEFAULT true,
    ingested_at   timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (url, version),
    UNIQUE (url, content_hash)
);
CREATE UNIQUE INDEX IF NOT EXISTS public_sources_one_current_idx ON knowledge.public_sources (url) WHERE is_current;

CREATE TABLE IF NOT EXISTS knowledge.rule_chunks (
    chunk_id        bigserial    PRIMARY KEY,
    source_id       bigint       NOT NULL REFERENCES knowledge.public_sources (source_id),
    chunk_index     integer      NOT NULL CHECK (chunk_index >= 0),
    content         text         NOT NULL CHECK (length(content) BETWEEN 1 AND 4000),
    metadata        jsonb        NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    embedding_model text         NOT NULL,
    embedding       vector(256)  NOT NULL,
    UNIQUE (source_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS rule_chunks_embedding_idx ON knowledge.rule_chunks USING hnsw (embedding vector_cosine_ops);

-- Fontes e chunks nunca sao apagados nem reescritos; apenas is_current muda (trigger).
CREATE OR REPLACE FUNCTION knowledge.sources_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (NEW.source_id, NEW.url, NEW.title, NEW.publisher, NEW.consulted_at, NEW.license_note, NEW.content_hash, NEW.version, NEW.ingested_at)
       IS NOT DISTINCT FROM (OLD.source_id, OLD.url, OLD.title, OLD.publisher, OLD.consulted_at, OLD.license_note, OLD.content_hash, OLD.version, OLD.ingested_at) THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'knowledge.% e versionada: % bloqueado (apenas is_current pode mudar)', TG_TABLE_NAME, TG_OP USING ERRCODE = 'insufficient_privilege';
END
$$;

CREATE OR REPLACE FUNCTION knowledge.chunks_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'knowledge.rule_chunks e versionada: % bloqueado', TG_OP USING ERRCODE = 'insufficient_privilege';
END
$$;

DROP TRIGGER IF EXISTS public_sources_row_guard ON knowledge.public_sources;
CREATE TRIGGER public_sources_row_guard BEFORE UPDATE OR DELETE ON knowledge.public_sources
    FOR EACH ROW EXECUTE FUNCTION knowledge.sources_guard();
DROP TRIGGER IF EXISTS rule_chunks_row_guard ON knowledge.rule_chunks;
CREATE TRIGGER rule_chunks_row_guard BEFORE UPDATE OR DELETE ON knowledge.rule_chunks
    FOR EACH ROW EXECUTE FUNCTION knowledge.chunks_immutable();

-- Menor privilegio: etl ingere; api_ro e api_audit so leem (o agente consulta via ferramenta tipada).
GRANT USAGE ON SCHEMA knowledge TO fidelidade_etl, fidelidade_ro, fidelidade_api_audit;
GRANT SELECT, INSERT ON knowledge.public_sources, knowledge.rule_chunks TO fidelidade_etl;
GRANT UPDATE (is_current) ON knowledge.public_sources TO fidelidade_etl;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA knowledge TO fidelidade_etl;
GRANT SELECT ON knowledge.public_sources, knowledge.rule_chunks TO fidelidade_ro, fidelidade_api_audit;
REVOKE DELETE, TRUNCATE ON knowledge.public_sources, knowledge.rule_chunks FROM PUBLIC, fidelidade_etl, fidelidade_ro, fidelidade_api_audit;
