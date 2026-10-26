-- 001: schema analytics com as tabelas do contrato v1.1.0 (customer_features e route_metrics).
-- Tipos: string->text, integer->integer, decimal->numeric(14,2), boolean->boolean, date->date.
-- Dados 100% sinteticos; sem PII.

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE analytics.customer_features (
    customer_id             text           PRIMARY KEY,
    trips_12m               integer        NOT NULL CHECK (trips_12m >= 0),
    spend_12m_brl           numeric(14,2)  NOT NULL CHECK (spend_12m_brl >= 0),
    avg_ticket_brl          numeric(14,2)  NOT NULL CHECK (avg_ticket_brl >= 0),
    recency_days            integer        NOT NULL CHECK (recency_days BETWEEN 0 AND 365),
    preferred_route         text           NOT NULL,
    value_score             numeric(14,2)  NOT NULL CHECK (value_score BETWEEN 0 AND 100),
    segment                 text           NOT NULL CHECK (segment IN ('Estratégico', 'Frequente', 'Oportunidade', 'Em risco')),
    recommended_action      text           NOT NULL,
    points_balance          integer        NOT NULL CHECK (points_balance >= 0),
    margin_12m_brl          numeric(14,2)  NOT NULL CHECK (margin_12m_brl >= 0),
    disruptions_12m         integer        NOT NULL CHECK (disruptions_12m >= 0),
    complaints_12m          integer        NOT NULL CHECK (complaints_12m >= 0),
    hvs_clv                 numeric(14,2)  NOT NULL CHECK (hvs_clv BETWEEN 0 AND 100),
    hvs_margin              numeric(14,2)  NOT NULL CHECK (hvs_margin BETWEEN 0 AND 100),
    hvs_stability           numeric(14,2)  NOT NULL CHECK (hvs_stability BETWEEN 0 AND 100),
    hvs_cost_to_serve       numeric(14,2)  NOT NULL CHECK (hvs_cost_to_serve BETWEEN 0 AND 100),
    hvs                     numeric(14,2)  NOT NULL CHECK (hvs BETWEEN 0 AND 100),
    profile                 text           NOT NULL CHECK (profile IN ('A', 'B', 'C', 'D', 'E')),
    risk_score              numeric(14,2)  NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_drivers            text           NOT NULL,
    nba_action              text           NOT NULL,
    nba_expected_margin_brl numeric(14,2)  NOT NULL CHECK (nba_expected_margin_brl >= 0),
    nba_requires_approval   boolean        NOT NULL
);

CREATE INDEX customer_features_risk_idx ON analytics.customer_features (risk_score DESC);
CREATE INDEX customer_features_profile_idx ON analytics.customer_features (profile);

CREATE TABLE analytics.route_metrics (
    route             text           PRIMARY KEY CHECK (route ~ '^[A-Z]{3}-[A-Z]{3}$'),
    flights           integer        NOT NULL CHECK (flights >= 1),
    disrupted_flights integer        NOT NULL CHECK (disrupted_flights >= 0),
    avg_delay_minutes numeric(14,2)  NOT NULL CHECK (avg_delay_minutes >= 0),
    complaints        integer        NOT NULL CHECK (complaints >= 0),
    revenue_brl       numeric(14,2)  NOT NULL CHECK (revenue_brl >= 0),
    ivr               numeric(14,2)  NOT NULL CHECK (ivr BETWEEN 0 AND 100)
);
