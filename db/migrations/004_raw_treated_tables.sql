-- 004: tabelas das camadas raw (snapshot de origem) e treated (apos transformacao), conforme entidades
-- customers_raw / transactions_raw do contrato v1.1.0. Dados 100% sinteticos; sem PII.
-- Sem FK entre as tabelas: a integridade referencial e validada pelo pandera/contrato antes da carga.

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id       text     PRIMARY KEY CHECK (customer_id ~ '^C[0-9]{6}$'),
    signup_date       date     NOT NULL CHECK (signup_date <= DATE '2026-09-30'),
    loyalty_tier      text     NOT NULL CHECK (loyalty_tier IN ('Azul Fidelidade', 'Topázio', 'Safira', 'Diamante', 'Diamante Unique')),
    home_airport      text     NOT NULL CHECK (home_airport ~ '^[A-Z]{3}$'),
    preferred_channel text     NOT NULL CHECK (preferred_channel IN ('app', 'web', 'agency')),
    points_balance    integer  NOT NULL CHECK (points_balance >= 0),
    is_corporate      boolean  NOT NULL,
    primary_cabin     text     NOT NULL CHECK (primary_cabin IN ('economy', 'premium', 'business'))
);

CREATE TABLE IF NOT EXISTS raw.transactions (
    transaction_id    text           PRIMARY KEY,
    customer_id       text           NOT NULL,
    flight_date       date           NOT NULL CHECK (flight_date BETWEEN DATE '2025-10-01' AND DATE '2026-09-30'),
    origin            text           NOT NULL CHECK (origin ~ '^[A-Z]{3}$'),
    destination       text           NOT NULL CHECK (destination ~ '^[A-Z]{3}$'),
    amount_brl        numeric(14,2)  NOT NULL CHECK (amount_brl > 0),
    qualifying_points integer        NOT NULL CHECK (qualifying_points >= 0),
    cancelled         boolean        NOT NULL,
    margin_brl        numeric(14,2)  NOT NULL CHECK (margin_brl >= 0),
    delay_minutes     integer        NOT NULL CHECK (delay_minutes BETWEEN 0 AND 600),
    disrupted         boolean        NOT NULL,
    complaint_flag    boolean        NOT NULL,
    CHECK (origin <> destination)
);
CREATE INDEX IF NOT EXISTS raw_transactions_customer_idx ON raw.transactions (customer_id);

CREATE TABLE IF NOT EXISTS treated.customers (
    customer_id       text     PRIMARY KEY CHECK (customer_id ~ '^C[0-9]{6}$'),
    signup_date       date     NOT NULL CHECK (signup_date <= DATE '2026-09-30'),
    loyalty_tier      text     NOT NULL CHECK (loyalty_tier IN ('Azul Fidelidade', 'Topázio', 'Safira', 'Diamante', 'Diamante Unique')),
    home_airport      text     NOT NULL CHECK (home_airport ~ '^[A-Z]{3}$'),
    preferred_channel text     NOT NULL CHECK (preferred_channel IN ('app', 'web', 'agency')),
    points_balance    integer  NOT NULL CHECK (points_balance >= 0),
    is_corporate      boolean  NOT NULL,
    primary_cabin     text     NOT NULL CHECK (primary_cabin IN ('economy', 'premium', 'business'))
);

CREATE TABLE IF NOT EXISTS treated.transactions (
    transaction_id    text           PRIMARY KEY,
    customer_id       text           NOT NULL,
    flight_date       date           NOT NULL CHECK (flight_date BETWEEN DATE '2025-10-01' AND DATE '2026-09-30'),
    origin            text           NOT NULL CHECK (origin ~ '^[A-Z]{3}$'),
    destination       text           NOT NULL CHECK (destination ~ '^[A-Z]{3}$'),
    amount_brl        numeric(14,2)  NOT NULL CHECK (amount_brl > 0),
    qualifying_points integer        NOT NULL CHECK (qualifying_points >= 0),
    cancelled         boolean        NOT NULL,
    margin_brl        numeric(14,2)  NOT NULL CHECK (margin_brl >= 0),
    delay_minutes     integer        NOT NULL CHECK (delay_minutes BETWEEN 0 AND 600),
    disrupted         boolean        NOT NULL,
    complaint_flag    boolean        NOT NULL,
    CHECK (origin <> destination)
);
CREATE INDEX IF NOT EXISTS treated_transactions_customer_idx ON treated.transactions (customer_id);
