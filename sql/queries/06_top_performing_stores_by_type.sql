-- Top 3 stores by total revenue within each StoreType/Assortment segment (window function
-- ranking partitioned by segment), useful for identifying best-practice stores per format.
WITH store_totals AS (
    SELECT
        f.store_id,
        s.store_type,
        s.assortment,
        SUM(f.sales) AS total_sales
    FROM fact_sales f
    JOIN dim_store s ON s.store_id = f.store_id
    WHERE f.is_open
    GROUP BY f.store_id, s.store_type, s.assortment
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY store_type, assortment ORDER BY total_sales DESC
        ) AS rank_in_segment
    FROM store_totals
)
SELECT store_id, store_type, assortment, total_sales, rank_in_segment
FROM ranked
WHERE rank_in_segment <= 3
ORDER BY store_type, assortment, rank_in_segment;
