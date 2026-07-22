-- 7-day and 30-day trailing rolling average daily sales, per store, using window frames.
SELECT
    store_id,
    sale_date,
    sales,
    ROUND(AVG(sales) OVER (
        PARTITION BY store_id ORDER BY sale_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_avg_7d,
    ROUND(AVG(sales) OVER (
        PARTITION BY store_id ORDER BY sale_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_avg_30d,
    ROUND(STDDEV(sales) OVER (
        PARTITION BY store_id ORDER BY sale_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_std_30d
FROM fact_sales
WHERE is_open
  AND store_id = 1                      -- parameterize per store in application code
ORDER BY sale_date;
