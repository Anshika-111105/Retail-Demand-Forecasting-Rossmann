# Phase 5: SQL Analytics
## Retail Demand Forecasting & Inventory Optimization Platform

**Methodology Reference:** CRISP-DM — Phase 5 (Business Analytics / Modeling support)
**Database:** PostgreSQL
**Document Version:** 1.1 — schema and all 8 queries executed and validated against a real
PostgreSQL 16 instance loaded with the full processed dataset (1,115 stores / 1,017,209 rows)

---

## 1. Objective

Answer RetailX's core business-performance questions directly in SQL against a warehouse
representation of the Rossmann data, using CTEs and window functions so the same queries can back
both ad-hoc analysis and the Streamlit dashboard's data layer.

## 2. Schema

Defined in [`sql/schemas/01_create_tables.sql`](../sql/schemas/01_create_tables.sql):

- **`dim_store`** — one row per store (1,115 rows): format, assortment, competition, Promo2 metadata.
- **`fact_sales`** — one row per `(store_id, sale_date)` (~1.02M rows): the daily sales fact table,
  loaded from the Phase 3 processed dataset.

Both tables mirror the merged `data/processed/rossmann_train_store_merged.parquet` output —
`fact_sales` is loaded from `train`-derived columns, `dim_store` from `store.csv`.

## 3. Business Questions & Corresponding Queries

| # | Business Question | Query File | SQL Technique |
|---|---|---|---|
| 1 | Which stores generate the most revenue, and how does each rank chain-wide? | [`01_store_performance.sql`](../sql/queries/01_store_performance.sql) | `RANK()`, `PERCENT_RANK()` |
| 2 | How much do promotions actually lift sales, per store, controlling for weekday mix? | [`02_promotion_effectiveness.sql`](../sql/queries/02_promotion_effectiveness.sql) | CTE self-join on `(store, day_of_week)` |
| 3 | How much do state holidays and school holidays move sales vs. a normal day? | [`03_holiday_impact.sql`](../sql/queries/03_holiday_impact.sql) | CTE + `CROSS JOIN` baseline comparison |
| 4 | What is chain-wide monthly revenue, its running total, and month-over-month growth? | [`04_monthly_revenue_and_growth.sql`](../sql/queries/04_monthly_revenue_and_growth.sql) | `SUM() OVER`, `LAG() OVER` |
| 5 | What is a store's 7-day / 30-day rolling average and volatility? | [`05_rolling_averages.sql`](../sql/queries/05_rolling_averages.sql) | `AVG()`/`STDDEV()` with `ROWS BETWEEN` frame |
| 6 | Who are the top 3 stores within each store-format/assortment segment? | [`06_top_performing_stores_by_type.sql`](../sql/queries/06_top_performing_stores_by_type.sql) | `ROW_NUMBER() OVER (PARTITION BY ...)` |
| 7 | Is customer traffic growing, and is growth from more visits or bigger baskets? | [`07_customer_trends.sql`](../sql/queries/07_customer_trends.sql) | CTE + `LAG()` month-over-month delta |
| 8 | Which month/weekday combinations see the strongest seasonal demand? | [`08_seasonal_performance.sql`](../sql/queries/08_seasonal_performance.sql) | `GROUP BY` aggregation, dashboard heatmap source |

## 4. Why These Techniques

- **CTEs** keep each query readable as a sequence of named, testable steps (e.g. compute
  per-store-per-weekday averages first, then compare promo vs. non-promo), which mirrors how an
  analyst would reason through the question manually.
- **Window functions** (`RANK`, `ROW_NUMBER`, `PERCENT_RANK`, `LAG`, and framed `AVG`/`STDDEV`)
  avoid self-joins for ranking/rolling calculations, which is both faster and far less error-prone
  than the row-by-row alternative — critical at ~1M rows.
- All queries operate only on `is_open = TRUE` rows for sales-level aggregation, consistent with
  the Phase 3 decision to treat closed-store zero-sales as structural, not demand signal.

## 5. Validation

The schema and all 8 queries were executed against a PostgreSQL 16 instance loaded with the full
processed dataset (`dim_store`: 1,115 rows, `fact_sales`: 1,017,209 rows, 2013-01-01–2015-07-31 —
row counts and date range verified to match `data/processed/rossmann_train_store_merged.parquet`
exactly). One bug surfaced and was fixed: `01_store_performance.sql` originally called
`ROUND()` on `PERCENT_RANK()`'s raw `double precision` output, which PostgreSQL has no overload
for — fixed with an explicit `::NUMERIC` cast. Results were spot-checked for plausibility, e.g.:

- Promotion uplift ranges up to ~100% for the most promo-responsive stores.
- Easter/Christmas holidays show +40–42% average sales vs. a normal day; ordinary
  `school_holiday` days show a much smaller +3.5% effect — consistent with the two holiday types
  being different in kind, not just degree.
- Sunday (`day_of_week = 7`) shows far fewer observations than other weekdays (~200–400 vs.
  ~13,000–15,000 per month) but a much higher average — expected, since most stores are closed on
  Sundays and only a handful of exception stores trade, at unusually high volume.

## 6. Consumption

These queries (or parameterized variants of them) back:
- The **Streamlit dashboard's** Store Performance, Promotion Analytics, Holiday Impact, and KPI
  pages (see [Phase6_Dashboard_Design.md](Phase6_Dashboard_Design.md)).
- Ad-hoc business-analyst investigation via any PostgreSQL client.
- Sanity-checking feature engineering outputs (e.g. `05_rolling_averages.sql` should match the
  `sales_rolling_mean_7`/`sales_rolling_std_7` features computed in pandas).
