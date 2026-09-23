-- Requires delivery_features and route_distances views created in the notebook.
-- Compares single-seller routes from SP over the same 300-500 km range.
-- Grain of comparable_routes: one row per order.

WITH comparable_routes AS (
    SELECT
        df.order_id,
        rd.seller_state,
        rd.customer_state,
        rd.straight_line_distance_km,
        df.is_late,
        df.delay_days,
        EXTRACT(
            EPOCH FROM (
                df.order_delivered_carrier_date - df.order_purchase_timestamp
            )
        ) / 86400.0 AS purchase_to_carrier_days,
        EXTRACT(
            EPOCH FROM (
                df.order_delivered_customer_date - df.order_delivered_carrier_date
            )
        ) / 86400.0 AS carrier_to_customer_days,
        EXTRACT(
            EPOCH FROM (
                df.order_delivered_customer_date - df.order_purchase_timestamp
            )
        ) / 86400.0 AS actual_delivery_days,
        EXTRACT(
            EPOCH FROM (
                df.order_estimated_delivery_date - df.order_purchase_timestamp
            )
        ) / 86400.0 AS promised_delivery_days
    FROM delivery_features AS df
    JOIN route_distances AS rd USING (order_id)
    WHERE rd.seller_state = 'SP'
      AND rd.customer_state IN ('SP', 'RJ')
      AND rd.straight_line_distance_km >= 300
      AND rd.straight_line_distance_km < 500
      AND df.order_delivered_carrier_date >= df.order_purchase_timestamp
      AND df.order_delivered_customer_date >= df.order_delivered_carrier_date
)
SELECT
    seller_state || ' -> ' || customer_state AS route,
    COUNT(*) AS orders_count,
    ROUND(AVG(straight_line_distance_km), 1) AS average_distance_km,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_late) / COUNT(*),
        2
    ) AS late_share_pct,
    ROUND(AVG(purchase_to_carrier_days), 2) AS purchase_to_carrier_days,
    ROUND(AVG(carrier_to_customer_days), 2) AS carrier_to_customer_days,
    ROUND(AVG(actual_delivery_days), 2) AS actual_delivery_days,
    ROUND(AVG(promised_delivery_days), 2) AS promised_delivery_days,
    QUANTILE_CONT(delay_days, 0.75) AS delay_p75,
    QUANTILE_CONT(delay_days, 0.90) AS delay_p90,
    QUANTILE_CONT(delay_days, 0.95) AS delay_p95
FROM comparable_routes
GROUP BY seller_state, customer_state
ORDER BY customer_state;
