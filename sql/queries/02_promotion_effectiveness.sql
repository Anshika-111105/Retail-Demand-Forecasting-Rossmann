-- Promotion effectiveness: compare average sales on promo vs. non-promo days,
-- per store, controlling for day-of-week (a promo mostly running on Saturdays
-- should not be compared against a Tuesday-heavy non-promo baseline).
WITH by_promo_dow AS (
    SELECT
        store_id,
        day_of_week,
        is_promo,
        AVG(sales) AS avg_sales,
        COUNT(*)   AS n_days
    FROM fact_sales
    WHERE is_open
    GROUP BY store_id, day_of_week, is_promo
),
paired AS (
    SELECT
        promo.store_id,
        promo.day_of_week,
        promo.avg_sales  AS promo_avg_sales,
        base.avg_sales   AS non_promo_avg_sales
    FROM by_promo_dow promo
    JOIN by_promo_dow base
      ON base.store_id = promo.store_id
     AND base.day_of_week = promo.day_of_week
     AND base.is_promo = FALSE
    WHERE promo.is_promo = TRUE
)
SELECT
    store_id,
    ROUND(AVG(promo_avg_sales), 2)                                            AS avg_promo_sales,
    ROUND(AVG(non_promo_avg_sales), 2)                                        AS avg_non_promo_sales,
    ROUND(AVG(promo_avg_sales) - AVG(non_promo_avg_sales), 2)                 AS uplift_absolute,
    ROUND(100.0 * (AVG(promo_avg_sales) - AVG(non_promo_avg_sales))
          / NULLIF(AVG(non_promo_avg_sales), 0), 1)                           AS uplift_pct
FROM paired
GROUP BY store_id
ORDER BY uplift_pct DESC
LIMIT 50;
