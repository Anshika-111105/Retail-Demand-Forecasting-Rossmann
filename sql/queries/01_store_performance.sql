-- Store performance ranking: total revenue, average daily sales, sales-per-customer,
-- and a percentile rank across the chain. Only open days count towards performance.
WITH store_daily AS (
    SELECT
        store_id,
        SUM(sales)                                   AS total_sales,
        SUM(customers)                                AS total_customers,
        COUNT(*) FILTER (WHERE is_open)               AS days_open,
        AVG(sales) FILTER (WHERE is_open)             AS avg_daily_sales
    FROM fact_sales
    GROUP BY store_id
)
SELECT
    sd.store_id,
    ds.store_type,
    ds.assortment,
    sd.days_open,
    sd.total_sales,
    ROUND(sd.avg_daily_sales, 2)                                  AS avg_daily_sales,
    ROUND(sd.total_sales::NUMERIC / NULLIF(sd.total_customers, 0), 2) AS sales_per_customer,
    RANK() OVER (ORDER BY sd.total_sales DESC)                    AS revenue_rank,
    ROUND((PERCENT_RANK() OVER (ORDER BY sd.total_sales) * 100)::NUMERIC, 1) AS revenue_percentile
FROM store_daily sd
JOIN dim_store ds ON ds.store_id = sd.store_id
ORDER BY sd.total_sales DESC
LIMIT 50;
