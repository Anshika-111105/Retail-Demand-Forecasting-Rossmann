-- Customer traffic trend per store: month-over-month change in average daily customers,
-- and sales-per-customer trend, to distinguish "more visits" growth from "bigger basket" growth.
WITH monthly_store AS (
    SELECT
        store_id,
        DATE_TRUNC('month', sale_date)::DATE AS sale_month,
        AVG(customers)                        AS avg_customers,
        AVG(sales)::NUMERIC / NULLIF(AVG(customers), 0) AS avg_sales_per_customer
    FROM fact_sales
    WHERE is_open
    GROUP BY store_id, sale_month
)
SELECT
    store_id,
    sale_month,
    ROUND(avg_customers, 1)          AS avg_customers,
    ROUND(avg_sales_per_customer, 2) AS avg_sales_per_customer,
    ROUND(
        avg_customers - LAG(avg_customers) OVER (PARTITION BY store_id ORDER BY sale_month), 1
    ) AS customer_change_vs_prev_month
FROM monthly_store
ORDER BY store_id, sale_month;
