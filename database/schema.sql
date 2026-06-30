-- ==========================================================
-- SENTINEL DATABASE SCHEMA
-- ==========================================================

CREATE SCHEMA IF NOT EXISTS sentinel;

CREATE TABLE IF NOT EXISTS sentinel.market_prices (

    id BIGSERIAL PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,

    trade_date DATE NOT NULL,

    open NUMERIC(18,6),

    high NUMERIC(18,6),

    low NUMERIC(18,6),

    close NUMERIC(18,6),

    adjusted_close NUMERIC(18,6),

    volume BIGINT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);