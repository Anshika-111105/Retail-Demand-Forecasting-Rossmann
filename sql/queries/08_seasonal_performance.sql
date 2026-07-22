-- Seasonal (day-of-week x month) demand heatmap source data: average sales per
-- (month, day_of_week) cell, chain-wide, to power a dashboard seasonality heatmap.
SELECT
    EXTRACT(MONTH FROM sale_date)::INT AS month_num,
    day_of_week,
    ROUND(AVG(sales), 2)               AS avg_sales,
    COUNT(*)                            AS n_observations
FROM fact_sales
WHERE is_open
GROUP BY month_num, day_of_week
ORDER BY month_num, day_of_week;
