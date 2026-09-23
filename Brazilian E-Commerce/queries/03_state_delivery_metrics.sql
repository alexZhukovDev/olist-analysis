-- Requires delivery_features view created in the notebook.
-- Grain of the final result: one row per customer state.

SELECT
    c.customer_state,
    COUNT(*) AS delivered_orders,
    COUNT(*) FILTER (WHERE df.is_late) AS late_orders,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE df.is_late) / COUNT(*),
        2
    ) AS late_share_pct,
    ROUND(AVG(df.delivery_days), 2) AS average_delivery_days
FROM delivery_features AS df
JOIN customers AS c
    ON df.customer_id = c.customer_id
GROUP BY c.customer_state
ORDER BY delivered_orders DESC;
