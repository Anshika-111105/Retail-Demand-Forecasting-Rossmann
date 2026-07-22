-- Rossmann Store Sales — warehouse schema (PostgreSQL)
-- Grain: dim_store one row per store; fact_sales one row per (store_id, sale_date)

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_store;

CREATE TABLE dim_store (
    store_id                       INTEGER PRIMARY KEY,
    store_type                     CHAR(1) NOT NULL,          -- a/b/c/d
    assortment                     CHAR(1) NOT NULL,          -- a=basic, b=extra, c=extended
    competition_distance_m         NUMERIC,                   -- NULL = no tracked competitor
    competition_open_since_month   SMALLINT,
    competition_open_since_year    SMALLINT,
    promo2_enrolled                BOOLEAN NOT NULL,
    promo2_since_week              SMALLINT,
    promo2_since_year              SMALLINT,
    promo_interval                 TEXT                        -- e.g. 'Jan,Apr,Jul,Oct'
);

CREATE TABLE fact_sales (
    store_id            INTEGER NOT NULL REFERENCES dim_store (store_id),
    sale_date           DATE NOT NULL,
    day_of_week          SMALLINT NOT NULL,      -- 1=Monday ... 7=Sunday
    sales                NUMERIC NOT NULL,
    customers            INTEGER NOT NULL,
    is_open              BOOLEAN NOT NULL,
    is_promo             BOOLEAN NOT NULL,
    state_holiday         CHAR(1) NOT NULL DEFAULT '0',  -- 0=none, a=public, b=easter, c=christmas
    is_school_holiday     BOOLEAN NOT NULL,
    PRIMARY KEY (store_id, sale_date)
);

CREATE INDEX idx_fact_sales_date ON fact_sales (sale_date);
CREATE INDEX idx_fact_sales_store ON fact_sales (store_id);
CREATE INDEX idx_fact_sales_promo ON fact_sales (is_promo);
