CREATE TABLE IF NOT EXISTS sentinel.market_features (

    id BIGSERIAL PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,

    trade_date DATE NOT NULL,

    simple_return DOUBLE PRECISION,
    log_return DOUBLE PRECISION,
    cumulative_return DOUBLE PRECISION,

    return_5d DOUBLE PRECISION,
    return_20d DOUBLE PRECISION,
    return_60d DOUBLE PRECISION,
    return_252d DOUBLE PRECISION,

    volatility_20d DOUBLE PRECISION,
    volatility_60d DOUBLE PRECISION,
    volatility_252d DOUBLE PRECISION,

    annualized_volatility_20d DOUBLE PRECISION,
    annualized_volatility_60d DOUBLE PRECISION,
    annualized_volatility_252d DOUBLE PRECISION,

    volatility_acceleration DOUBLE PRECISION,

    rolling_peak DOUBLE PRECISION,
    drawdown DOUBLE PRECISION,
    max_drawdown DOUBLE PRECISION,

    sma_20 DOUBLE PRECISION,
    sma_50 DOUBLE PRECISION,
    sma_200 DOUBLE PRECISION,

    ema_20 DOUBLE PRECISION,
    ema_50 DOUBLE PRECISION,

    momentum_20 DOUBLE PRECISION,
    roc_20 DOUBLE PRECISION,

    distance_sma20 DOUBLE PRECISION,
    distance_sma50 DOUBLE PRECISION,
    distance_sma200 DOUBLE PRECISION,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_market_features
    UNIQUE(symbol, trade_date)

);