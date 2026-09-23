-- Requires delivery_features and clean_reviews views created in the notebook.
-- Grain of bucketed: one row per delivered order with one selected review.

WITH bucketed AS (
    SELECT
        df.order_id,
        cr.review_score,
        df.delay_days,
        CASE
            WHEN df.delay_days <= 0 THEN 0
            WHEN df.delay_days = 1 THEN 1
            WHEN df.delay_days BETWEEN 2 AND 3 THEN 2
            WHEN df.delay_days BETWEEN 4 AND 7 THEN 3
            WHEN df.delay_days BETWEEN 8 AND 14 THEN 4
            WHEN df.delay_days BETWEEN 15 AND 30 THEN 5
            ELSE 6
        END AS delay_bucket_num,
        CASE
            WHEN df.delay_days <= 0 THEN 'On time'
            WHEN df.delay_days = 1 THEN '1 day'
            WHEN df.delay_days BETWEEN 2 AND 3 THEN '2-3 days'
            WHEN df.delay_days BETWEEN 4 AND 7 THEN '4-7 days'
            WHEN df.delay_days BETWEEN 8 AND 14 THEN '8-14 days'
            WHEN df.delay_days BETWEEN 15 AND 30 THEN '15-30 days'
            ELSE '31+ days'
        END AS delay_bucket
    FROM delivery_features AS df
    JOIN clean_reviews AS cr USING (order_id)
)
SELECT
    delay_bucket_num,
    delay_bucket,
    COUNT(*) AS orders_count,
    ROUND(AVG(review_score), 2) AS average_review_score
FROM bucketed
GROUP BY delay_bucket_num, delay_bucket
ORDER BY delay_bucket_num;
