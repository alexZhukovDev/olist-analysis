-- Grain of delivered_orders: one row per order.
-- Grain of the final result: one row per purchase month.

WITH delivered_orders AS (
    SELECT
        o.order_id,
        o.order_purchase_timestamp,
        SUM(oi.price) AS products_total,
        SUM(oi.freight_value) AS freight_total,
        SUM(oi.price + oi.freight_value) AS gross_order_value
    FROM orders AS o
    JOIN order_items AS oi USING (order_id)
    WHERE o.order_status = 'delivered'
    GROUP BY o.order_id, o.order_purchase_timestamp
),
monthly AS (
    SELECT
        DATE_TRUNC('month', order_purchase_timestamp) AS month,
        COUNT(*) AS delivered_orders,
        SUM(gross_order_value) AS gross_order_value,
        AVG(gross_order_value) AS average_order_value,
        SUM(products_total) AS products_total,
        SUM(freight_total) AS freight_total
    FROM delivered_orders
    GROUP BY month
),
analysis_period AS (
    SELECT *
    FROM monthly
    WHERE month BETWEEN DATE '2017-01-01' AND DATE '2018-08-01'
),
with_previous AS (
    SELECT
        *,
        LAG(gross_order_value) OVER (ORDER BY month) AS previous_month_gov
    FROM analysis_period
)
SELECT
    month,
    delivered_orders,
    ROUND(gross_order_value, 2) AS gross_order_value,
    ROUND(average_order_value, 2) AS average_order_value,
    ROUND(products_total, 2) AS products_total,
    ROUND(freight_total, 2) AS freight_total,
    ROUND(100.0 * freight_total / NULLIF(gross_order_value, 0), 2)
        AS freight_share_pct,
    ROUND(
        100.0 * (gross_order_value - previous_month_gov)
        / NULLIF(previous_month_gov, 0),
        2
    ) AS mom_gov_pct
FROM with_previous
ORDER BY month;
