-- Chain-wide monthly revenue with running total and month-over-month growth %.
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', sale_date)::DATE AS sale_month,
        SUM(sales)                            AS monthly_sales
    FROM fact_sales
    WHERE is_open
    GROUP BY sale_month
)
SELECT
    sale_month,
    monthly_sales,
    SUM(monthly_sales) OVER (ORDER BY sale_month)                              AS running_total_sales,
    LAG(monthly_sales) OVER (ORDER BY sale_month)                              AS prev_month_sales,
    ROUND(
        100.0 * (monthly_sales - LAG(monthly_sales) OVER (ORDER BY sale_month))
        / NULLIF(LAG(monthly_sales) OVER (ORDER BY sale_month), 0), 1
    )                                                                          AS mom_growth_pct
FROM monthly
ORDER BY sale_month;
