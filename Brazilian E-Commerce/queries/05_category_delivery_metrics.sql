-- An order with multiple categories contributes once to each category.
-- Grain of order_categories: one row per order-category pair.

WITH order_categories AS (
    SELECT DISTINCT
        oi.order_id,
        COALESCE(
            t.product_category_name_english,
            p.product_category_name
        ) AS category
    FROM order_items AS oi
    JOIN products AS p USING (product_id)
    LEFT JOIN translation AS t
        ON p.product_category_name = t.product_category_name
)
SELECT
    oc.category,
    COUNT(*) AS delivered_orders,
    COUNT(*) FILTER (WHERE df.is_late) AS late_orders,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE df.is_late) / COUNT(*),
        2
    ) AS late_share_pct,
    ROUND(AVG(df.delivery_days), 2) AS average_delivery_days
FROM order_categories AS oc
JOIN delivery_features AS df USING (order_id)
WHERE oc.category IS NOT NULL
GROUP BY oc.category
HAVING COUNT(*) > 500
ORDER BY late_share_pct DESC, delivered_orders DESC;
