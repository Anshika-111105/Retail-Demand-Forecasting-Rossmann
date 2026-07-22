-- Holiday impact: average sales on each state-holiday type vs. an ordinary day baseline,
-- plus school-holiday effect, chain-wide.
WITH holiday_avg AS (
    SELECT
        CASE state_holiday
            WHEN 'a' THEN 'public_holiday'
            WHEN 'b' THEN 'easter_holiday'
            WHEN 'c' THEN 'christmas_holiday'
            ELSE 'none'
        END AS holiday_type,
        AVG(sales) AS avg_sales,
        COUNT(*)   AS n_days
    FROM fact_sales
    WHERE is_open
    GROUP BY holiday_type
),
baseline AS (
    SELECT avg_sales AS baseline_avg_sales FROM holiday_avg WHERE holiday_type = 'none'
),
school_holiday_avg AS (
    SELECT
        is_school_holiday,
        AVG(sales) AS avg_sales,
        COUNT(*)   AS n_days
    FROM fact_sales
    WHERE is_open
    GROUP BY is_school_holiday
)
SELECT
    h.holiday_type,
    h.n_days,
    ROUND(h.avg_sales, 2)                                              AS avg_sales,
    ROUND(100.0 * (h.avg_sales - b.baseline_avg_sales) / b.baseline_avg_sales, 1) AS pct_vs_normal_day
FROM holiday_avg h
CROSS JOIN baseline b
UNION ALL
SELECT
    CASE WHEN is_school_holiday THEN 'school_holiday' ELSE 'no_school_holiday' END,
    n_days,
    ROUND(avg_sales, 2),
    ROUND(100.0 * (avg_sales - (SELECT baseline_avg_sales FROM baseline))
          / (SELECT baseline_avg_sales FROM baseline), 1)
FROM school_holiday_avg
ORDER BY pct_vs_normal_day DESC;
