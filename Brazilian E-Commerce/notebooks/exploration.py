# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: .venv (3.12.10.final.0)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Анализ продаж и выполнения заказов Olist
#
# ## Цель проекта
#
# Оценить динамику продаж маркетплейса и качество выполнения заказов,
# выявить проблемные периоды и факторы, связанные со сроками доставки
# и удовлетворённостью покупателей.
#
# ## Задачи
#
# - исследовать динамику заказов, валовой стоимости и среднего чека;
# - оценить долю успешно доставленных и незавершённых заказов;
# - проанализировать сроки и опоздания доставки;
# - проверить связь логистики с географией, категориями и отзывами;
# - сформулировать выводы и ограничения анализа.

# %%
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path

# %%
DATA_DIR = Path("../data/raw")

# %%
con = duckdb.connect()

# %%
list(DATA_DIR.glob("*.csv"))

# %% [markdown]
# ### Загрузка и первичное знакомство с данными

# %%
con.sql("""
    SELECT * 
    FROM read_csv_auto('../data/raw/olist_customers_dataset.csv') 
    LIMIT 5
""").df()

# %%
con.sql("""
    CREATE VIEW customers AS 
    SELECT *
    FROM read_csv_auto('../data/raw/olist_customers_dataset.csv') 
""")

# %%
con.sql("""
    SELECT COUNT(*)
    FROM customers
""")

# %%
con.sql("""
    CREATE VIEW orders AS 
    SELECT * 
    FROM read_csv_auto('../data/raw/olist_orders_dataset.csv')
""")

# %%
con.sql("""
    SELECT * 
    FROM orders 
    LIMIT 5
""")

# %%
con.sql("""
    SELECT COUNT(order_id) 
    FROM orders 
""")

# %%
con.sql("""
    SELECT COUNT(DISTINCT order_id) 
    FROM orders 
""")

# %%
con.sql("""
    SELECT order_status, COUNT(*)
    FROM orders
    GROUP BY order_status
""")

# %%
con.sql("""
    CREATE VIEW order_items AS 
    SELECT * 
    FROM read_csv_auto('../data/raw/olist_order_items_dataset.csv')
""")

# %%
con.sql("""
    SELECT DISTINCT COUNT(order_id) 
    FROM order_items
""")

# %%
con.sql("""
    SELECT *
    FROM order_items
    LIMIT 5
""")

# %%
con.sql("""
    SELECT order_id, COUNT(*) as cnt, COUNT(DISTINCT product_id) as unique
    FROM order_items
    GROUP BY order_id
    ORDER BY cnt DESC
    LIMIT 10
""")

# %% [markdown]
# ### Расчёт стоимости доставленных заказов

# %%
con.sql("""
    SELECT DISTINCT order_item_id as id
    FROM order_items
    ORDER BY id desc
""")

# %%
con.sql("""
    SELECT order_id, order_purchase_timestamp, product_id, price, freight_value
    FROM orders 
        INNER JOIN order_items USING (order_id)
    WHERE (order_status = 'delivered')
""")

# %%
con.sql("""
    SELECT order_id, order_purchase_timestamp, SUM(price + freight_value) AS order_total
    FROM orders 
        INNER JOIN order_items USING (order_id)
    WHERE (order_status = 'delivered')
    GROUP BY order_id, order_purchase_timestamp
""")

# %%
con.sql("""
WITH delivered_orders AS (
SELECT order_id, order_purchase_timestamp, SUM(price + freight_value) AS order_total
FROM orders 
    INNER JOIN order_items USING (order_id)
WHERE (order_status = 'delivered')
GROUP BY order_id, order_purchase_timestamp
)
    
SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month, COUNT(*) AS delivered_orders, SUM(order_total) AS revenue, AVG(order_total) AS average_order_value
FROM delivered_orders
GROUP BY month
ORDER BY month ASC;

""")

# %%
con.sql("""
WITH delivered_orders AS (
SELECT order_id, order_purchase_timestamp, SUM(price + freight_value) AS order_total
FROM orders 
    INNER JOIN order_items USING (order_id)
WHERE (order_status = 'delivered')
GROUP BY order_id, order_purchase_timestamp
)
        
SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp)
FROM delivered_orders
""")

# %%
con.sql("""
WITH all_orders AS (
SELECT order_id, order_purchase_timestamp, SUM(price + freight_value) AS order_total
FROM orders 
    INNER JOIN order_items USING (order_id)
GROUP BY order_id, order_purchase_timestamp
)
    
SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month, COUNT(*) AS all_orders, SUM(order_total) AS revenue, AVG(order_total) AS average_order_value
FROM all_orders
GROUP BY month
ORDER BY month ASC;
""")

# %% [markdown]
# ### Месячные метрики и MoM-динамика

# %%
con.sql("""
WITH delivered_orders AS (
SELECT 
    order_id, 
    order_purchase_timestamp, 
    SUM(price + freight_value) AS order_total,
    SUM(price) AS order_products_total,
    SUM(freight_value) as order_freight_total
FROM orders 
    INNER JOIN order_items USING (order_id)
WHERE (order_status = 'delivered')
GROUP BY order_id, order_purchase_timestamp
)
    
SELECT 
    DATE_TRUNC('month', order_purchase_timestamp) AS month, 
     COUNT(*) AS delivered_orders, 
    SUM(order_total) AS gross_order_value, 
    AVG(order_total) AS average_order_value,
    SUM(order_products_total) AS montly_products_total,
    SUM(order_freight_total) AS monthly_freight_total,
    ROUND((monthly_freight_total * 100 / NULLIF(gross_order_value, 0)), 1) AS freight_share_pct
FROM delivered_orders
GROUP BY month
ORDER BY month ASC;
""").df()

# %%
con.sql("""
WITH delivered_orders AS (
SELECT 
    order_id, 
    order_purchase_timestamp, 
    SUM(price + freight_value) AS order_total,
    SUM(price) AS order_products_total,
    SUM(freight_value) as order_freight_total
FROM orders 
    INNER JOIN order_items USING (order_id)
WHERE (order_status = 'delivered')
GROUP BY order_id, order_purchase_timestamp
),
monthly_metrics AS (
SELECT 
    DATE_TRUNC('month', order_purchase_timestamp) AS month, 
     COUNT(*) AS delivered_orders, 
    SUM(order_total) AS gross_order_value, 
    AVG(order_total) AS average_order_value,
    SUM(order_products_total) AS monthly_products_total,
    SUM(order_freight_total) AS monthly_freight_total,
    ROUND((monthly_freight_total * 100 / NULLIF(gross_order_value, 0)), 1) AS freight_share_pct
FROM delivered_orders
GROUP BY month
),
monthly_with_previous AS (
    SELECT
        month,
        gross_order_value,
        LAG(gross_order_value) OVER (ORDER BY month) AS previous_gov
    FROM monthly_metrics
    WHERE month >= DATE '2017-01-01'
        AND month <= DATE '2018-08-01'
)
        
SELECT 
    month,
    gross_order_value,
    gross_order_value - previous_gov AS mom_abs_diff,
    ROUND((gross_order_value - previous_gov) / NULLIF(previous_gov, 0) * 100, 1) AS mom_diff_pct
FROM monthly_with_previous
ORDER BY month;
""")

# %% [markdown]
# Вывод: таблица показывает помесячную динамику валовой стоимости доставленных заказов (gross_order_value), включающей стоимость товаров и доставки, а также её абсолютное и процентное изменение относительно предыдущего месяца. Динамика неравномерна: встречаются как месяцы роста, так и месяцы снижения.
# Основной период анализа начинается с января 2017 года. Данные за сентябрь–декабрь 2016 года фрагментарны: в сентябре и декабре присутствует только по одному доставленному заказу, а данные за ноябрь отсутствуют.
# Август 2018 года включён в таблицу, однако требует осторожной интерпретации: последний доставленный заказ по дате оформления относится к 29 августа, хотя в исходной таблице существуют заказы от 30–31 августа. Поэтому августовские показатели доставленных заказов могут быть занижены.

# %% [markdown]
# ### Анализ статусов заказов

# %%
con.sql("""
WITH monthly_order_status AS (
SELECT 
    DATE_TRUNC('month', order_purchase_timestamp) AS month, 
    order_status,
    COUNT(*) AS status_orders_count,
    SUM(COUNT(*)) OVER (PARTITION BY month) AS all_orders_count,
    ROUND(status_orders_count / (all_orders_count / 100), 1) AS share_pct,
    MIN(order_purchase_timestamp),
    MAX(order_purchase_timestamp)
FROM orders
GROUP BY month, order_status

)
        
SELECT 
    *
FROM monthly_order_status
ORDER BY month ASC
""")

# %%
con.sql("""
SELECT
    order_status AS status,
    COUNT(*) AS orders_count,
    COUNT(*) FILTER (WHERE order_delivered_carrier_date IS NULL) AS missing_carrier_date,
    COUNT(*) FILTER (WHERE order_delivered_customer_date IS NULL) AS missing_customer_date,
    COUNT(*) FILTER (WHERE order_approved_at IS NOT NULL AND order_delivered_carrier_date IS NULL) AS stuck_before_shipping,
    COUNT(*) FILTER (WHERE order_approved_at IS NOT NULL AND order_delivered_customer_date IS NULL AND order_delivered_carrier_date IS NOT NULL) AS stuck_in_delivery
FROM orders
WHERE order_status IN ('processing', 'invoiced', 'shipped')
  AND order_purchase_timestamp < DATE '2017-12-01'
GROUP BY status
""")

# %%
con.sql("""
WITH delivery_features AS (
SELECT 
    order_id, 
    order_delivered_customer_date - order_purchase_timestamp AS delivery_time,
    CAST(order_delivered_customer_date AS DATE) - CAST(order_estimated_delivery_date AS DATE) AS delay_days,
    delay_days > 0 AS is_late
FROM orders     
WHERE (order_status = 'delivered')
),
late_count AS (
SELECT 
    is_late, 
    COUNT(*) as orders_count,
    SUM(COUNT(*)) OVER () AS total_cnt,
    ROUND(orders_count * 100.0 / total_cnt, 2) AS late_pct
FROM delivery_features
WHERE is_late IS NOT NULL
GROUP BY is_late
)

SELECT * FROM late_count
""")

# %% [markdown]
# #### Среди заказов с известной датой доставки, **6.77%** заказов были доставлены позже обещанной календарной даты

# %% [markdown]
# ### Связь опозданий и ревью

# %%
con.sql("""
    CREATE VIEW reviews AS 
    SELECT *
    FROM read_csv_auto('../data/raw/olist_order_reviews_dataset.csv') 
""")

# %%
con.sql("""
SELECT 
    COUNT(DISTINCT review_id), 
    COUNT(DISTINCT order_id), 
    COUNT(*)
FROM reviews
""")

# %%
con.sql("""
SELECT order_id, COUNT(*) AS reviews_count
FROM reviews
GROUP BY order_id
HAVING COUNT(*) > 1
ORDER BY reviews_count DESC;
""")

# %%
con.sql("""
SELECT
    review_id,
    COUNT(*) AS rows_count,
    COUNT(DISTINCT order_id) AS orders_count
FROM reviews
GROUP BY review_id
HAVING COUNT(DISTINCT order_id) > 1
ORDER BY orders_count DESC;
""")

# %%
con.sql("""
    SELECT *
    FROM reviews
    WHERE (review_id = '4d0e6dd087008d1f992d25ef6e1f619f')
""")

# %%
con.sql("""
SELECT 
    review_score,
    COUNT(*) as review_cnt,
    SUM(COUNT(*)) OVER () AS total_reviews,
    -- AVG(review_score) OVER (),
    ROUND(review_cnt * 100 / total_reviews, 2) AS review_dist
FROM orders 
    INNER JOIN reviews USING (order_id)
GROUP BY review_score
ORDER BY review_score
""")

# %%
con.sql("""
WITH clean_reviews AS (
SELECT COUNT(*)
FROM reviews
GROUP BY review_id
HAVING COUNT(DISTINCT order_id) = 1
)
SELECT * FROM clean_reviews
""")

# %%
con.sql("""
WITH valid_review_ids AS (
    SELECT
        review_id
    FROM reviews
    GROUP BY review_id
    HAVING COUNT(DISTINCT order_id) = 1
),
valid_reviews AS (
SELECT reviews.*
FROM reviews    
    JOIN valid_review_ids USING (review_id)  
),
ranked_reviews AS (
SELECT 
    *,
    ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC, review_id) as review_rank
    FROM valid_reviews
),
clean_reviews AS (
    SELECT *
    FROM ranked_reviews
    WHERE review_rank = 1
), delivery_features AS (
SELECT 
    order_id, 
    order_delivered_customer_date - order_purchase_timestamp AS delivery_time,
    CAST(order_delivered_customer_date AS DATE) - CAST(order_estimated_delivery_date AS DATE) AS delay_days,
    delay_days > 0 AS is_late
FROM orders     
WHERE (order_status = 'delivered') AND is_late IS NOT NULL
)

SELECT 
    review_score, 
    is_late, 
    COUNT(*) as orders_count,
    SUM(COUNT(*)) OVER (PARTITION BY is_late) AS total_cnt,
    ROUND(orders_count * 100 / total_cnt, 2) AS share_within_delivery_group
    FROM delivery_features 
        JOIN clean_reviews USING (order_id)
    GROUP BY is_late, review_score
    ORDER BY is_late DESC, review_score DESC; 
""").df()

# %%
con.sql("""
WITH valid_review_ids AS (
    SELECT
        review_id
    FROM reviews
    GROUP BY review_id
    HAVING COUNT(DISTINCT order_id) = 1
),
valid_reviews AS (
SELECT reviews.*
FROM reviews    
    JOIN valid_review_ids USING (review_id)  
),
ranked_reviews AS (
SELECT 
    *,
    ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC, review_id) as review_rank
    FROM valid_reviews
)
SELECT * FROM ranked_reviews
""")

# %%
con.sql("""
WITH valid_review_ids AS (
    SELECT
        review_id
    FROM reviews
    GROUP BY review_id
    HAVING COUNT(DISTINCT order_id) = 1
),
        
valid_reviews AS (
SELECT reviews.*
FROM reviews    
    JOIN valid_review_ids USING (review_id)  
),
        
ranked_reviews AS (
SELECT 
    *,
    ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC, review_id) as review_rank
    FROM valid_reviews
),
        
clean_reviews AS (
    SELECT *
    FROM ranked_reviews
    WHERE review_rank = 1
), 

delivery_features AS (
SELECT 
    order_id, 
    order_delivered_customer_date - order_purchase_timestamp AS delivery_time,
    CAST(order_delivered_customer_date AS DATE) - CAST(order_estimated_delivery_date AS DATE) AS delay_days,
    delay_days > 0 AS is_late
FROM orders     
WHERE (order_status = 'delivered') AND is_late IS NOT NULL
),
        
bucketed_orders AS (
SELECT 
    df.order_id,
    df.delay_days,
    cr.review_score,
    CASE 
        WHEN df.delay_days = 1 THEN '1 day'
        WHEN df.delay_days BETWEEN 2 AND 3 THEN '2-3 days'
        WHEN df.delay_days BETWEEN 4 AND 7 THEN '4-7 days'
        WHEN df.delay_days BETWEEN 8 AND 14 THEN '8-14 days'
        WHEN df.delay_days BETWEEN 15 AND 30 THEN '15-30 days'
        ELSE '31+ days'
    END AS delay_bucket 
FROM delivery_features AS df
    INNER JOIN clean_reviews AS cr USING (order_id)
WHERE df.is_late = true
)
    
SELECT
    delay_bucket,
    COUNT(*) AS orders_count,
    ROUND(AVG(review_score), 2) AS average_review_score
FROM bucketed_orders
GROUP BY delay_bucket
ORDER BY MIN(delay_days)
""").df()

# %% [markdown]
# #### Вывод: с увеличением длительности задержки средняя оценка заказа в целом снижается. Для заказов, доставленных вовремя, оценка составялет 4.29 балла, при задержке в один день - 3.74, а при задержке 15-30 дней - 1.61. Наиболее заметное снижение наблюдается за первую неделю опоздания: средняя оценка падает с 3.74 при задержке на один день до 2.11 при задержке на 4-7 дней.
#
# #### На всём диапазоне зависимость не является строго монотонной: для задержке свыше 30 дней средняя оценка повышается до 2.05. Это может быть связано с составом группы и широким интервалом 31+, поэтому результат не следует интерпретировать как улучшение клиентского опыта при экстремальных задержках

# %% [markdown]
# ### Связь логистики и географии

# %%
con.sql("""
SELECT COUNT(DISTINCT customer_id) 
FROM customers
""")

# %%
con.sql("""
WITH delivery_features AS (
SELECT 
    order_id, 
    EXTRACT(
        EPOCH FROM (
            order_delivered_customer_date - order_purchase_timestamp
        )
    ) / 86400.0 AS delivery_days,
    CAST(order_delivered_customer_date AS DATE) - CAST(order_estimated_delivery_date AS DATE) AS delay_days,
    delay_days > 0 AS is_late
FROM orders     
WHERE (order_status = 'delivered') AND is_late IS NOT NULL
)
        
SELECT 
    customer_state,
    COUNT(*) FILTER (WHERE is_late = true) as late_orders,
    COUNT(*) AS delivered_orders,
    late_orders / NULLIF(delivered_orders, 0) * 100 late_share_pct,
    ROUND(AVG(delivery_days), 2) average_delivery_time
FROM delivery_features df
    JOIN orders USING (order_id)
    JOIN customers USING (customer_id)
GROUP BY customer_state
ORDER BY delivered_orders DESC, late_share_pct DESC;
""")

# %%
state_metrics = con.sql("""
WITH delivery_features AS (
SELECT 
    order_id, 
    EXTRACT(
        EPOCH FROM (
            order_delivered_customer_date - order_purchase_timestamp
        )
    ) / 86400.0 AS delivery_days,
    CAST(order_delivered_customer_date AS DATE) - CAST(order_estimated_delivery_date AS DATE) AS delay_days,
    delay_days > 0 AS is_late
FROM orders     
WHERE (order_status = 'delivered') AND is_late IS NOT NULL
)
        
SELECT 
    customer_state,
    COUNT(*) FILTER (WHERE is_late = true) as late_orders,
    COUNT(*) AS delivered_orders,
    late_orders / NULLIF(delivered_orders, 0) * 100 late_share_pct,
    ROUND(AVG(delivery_days), 2) average_delivery_time
FROM delivery_features df
    JOIN orders USING (order_id)
    JOIN customers USING (customer_id)
GROUP BY customer_state
ORDER BY delivered_orders DESC, late_share_pct DESC;
""").df()

# %%
plot_data = (
    state_metrics
    .query("delivered_orders >= 500")
    .sort_values("late_share_pct")
    .copy()
)

plot_data["state_label"] = (
    plot_data["customer_state"]
    + " (n="
    + plot_data["delivered_orders"].astype(str)
    + ")"
)

# %%
fig, ax = plt.subplots(figsize=(9, 7))

sns.barplot(
    data=plot_data,
    x="late_share_pct",
    y="state_label",
    color="steelblue",
    ax=ax
)

ax.bar_label(
    ax.containers[0],
    fmt="%.1f%%",
    padding=3
)

ax.set(
    title="Доля опоздавших доставок по штатам",
    xlabel="Доля опоздавших заказов, %",
    ylabel="Штат и количество доставленных заказов"
)

sns.despine()
plt.tight_layout()
plt.show()

# %% [markdown]
# ### Связь логистики и категорий товаров

# %%
con.sql("""
    CREATE VIEW products AS 
    SELECT *
    FROM read_csv_auto('../data/raw/olist_products_dataset.csv') 
""")

# %%
con.sql("""
    CREATE VIEW translation AS 
    SELECT *
    FROM read_csv_auto('../data/raw/product_category_name_translation.csv') 
""")

# %%
con.sql("""
WITH order_category_counts AS (
SELECT 
    order_id,
    COUNT(DISTINCT product_category_name) as categories_count,
FROM order_items
    JOIN products USING (product_id)
GROUP BY order_id
)
SELECT 
    CASE 
        WHEN categories_count = 1 THEN 'one_category' 
        WHEN categories_count > 1 THEN 'few_categories' 
        ELSE 'unknown_category'
    END AS category_group,
    COUNT(*) AS orders_count
FROM order_category_counts
GROUP BY category_group
""")

# %%
con.sql("""
WITH order_categories AS (
SELECT DISTINCT 
    order_id, 
    COALESCE(
        t.product_category_name_english,
        p.product_category_name) as category
FROM order_items oi 
    JOIN products p USING (product_id)
    LEFT JOIN translation t ON p.product_category_name = t.product_category_name
),
delivery_features AS (
SELECT 
    order_id, 
    EXTRACT(
        EPOCH FROM (
            order_delivered_customer_date - order_purchase_timestamp
        )
    ) / 86400.0 AS delivery_days,
    CAST(order_delivered_customer_date AS DATE) - CAST(order_estimated_delivery_date AS DATE) AS delay_days,
    delay_days > 0 AS is_late
FROM orders     
WHERE (order_status = 'delivered') AND is_late IS NOT NULL
)
        
SELECT 
    category, 
    COUNT(*) AS delivered_orders,
    COUNT(*) FILTER (WHERE is_late = TRUE) AS late_orders,
    ROUND((late_orders / delivered_orders) * 100, 2) AS late_share_pct,
    ROUND(AVG(delivery_days), 2) AS average_delivery_days
FROM order_categories oc
    JOIN delivery_features USING (order_id)
WHERE (category IS NOT NULL)
GROUP BY category
HAVING (delivered_orders > 500)
ORDER BY late_share_pct DESC, delivered_orders DESC;
""")

# %% [markdown]
# #### Среди массовых категорий не обнаружено экстремально высокой доли опозданий. Категории bebes, eletronicos, beleza_saude, cama_mesa_banho и relogios_presentes умеренно превышают общий уровень задержек. Наиболее заметно выделяется moveis_escritorio: помимо доли опозданий выше среднего, эта категория имеет средний срок доставки 20,64 дня, что существенно выше большинства массовых категорий.
# #### Наблюдаемые различия не позволяют считать категорию непосредственной причиной задержек: они могут быть связаны с габаритами товаров, расположением продавцов и покупателей или особенностями обработки заказов.

# %% [markdown]
# ## Выводы:
#
# ### Опоздания и отзывы:
# **Наблюдение:** с увеличением длительности задержки доставки средняя оценка заказа в целом снижается. Для заказов, доставленных вовремя, оценка составялет 4,29 балла, при задержке в один день - 3,74, а при задержке 15-30 дней - 1,61.
#
# **Возможное объяснение:** задержка доставки может ухудшать клиентский опыт и быть одной из причин более низкой оценки товара
#
# **Ограничение:** на оценку может влиять не только задержка доставки, но и, например, качество товара
#
# **Рекомендация:** рекомендуется в первую очередь выяснить основные причины задержек доставки, поскольку уже в течение первой недели опоздания средняя оценка снижается с 4,29 для своевременно доставленных заказов до 2,11 для заказов с задержкой 4–7 дней.
#
# ### География: 
# **Наблюдение:** штат SP, в который было доставлено наибольшее количество заказов, имеет долю опоздавших доставленных заказов около 4,5%, тогда как штаты RJ, BA, CE, MA имеют заметно более высокую долю опозданий, например для RJ доля заказов, доставленных не в срок, составила 12,1%
#
# **Возможное объяснение:** различия могут быть связаны с расстоянием между продавцами и покупателями, распределением продавцов по регионам и особенностями региональной логистической инфраструктуры.
#
# **Ограничение:** нельзя утверждать точную причину задержек логистики из имеющейся статистики.
#
# **Рекомендация:** в первую очередь рекомендуется подробнее исследовать доставки в штат RJ, проверив связь опозданий с расстоянием между продавцами и покупателями, поскольку штат сочетает большой объём заказов и высокую долю доставок с нарушением обещанного срока.

# %% [markdown]
# ### Анализ связи географии и опозданий. 
# Вопрос: почему RJ имеет долю опозданий доставок почти в 2.7 раза выше, чем штата SP?

# %%
con.sql("""
    CREATE VIEW sellers AS 
    SELECT *
    FROM read_csv_auto('../data/raw/olist_sellers_dataset.csv') 
""")
con.sql("""
    CREATE VIEW geolocation AS 
    SELECT *
    FROM read_csv_auto('../data/raw/olist_geolocation_dataset.csv') 
""")

# %%
con.sql("""
SELECT 
    geolocation_zip_code_prefix, 
    COUNT(*) as sum_count,
    COUNT(DISTINCT geolocation_lat)
FROM geolocation
GROUP BY geolocation_zip_code_prefix
ORDER BY geolocation_zip_code_prefix ASC;
""")

# %%
con.sql("""
SELECT 
    COUNT(*), 
    COUNT(DISTINCT geolocation_zip_code_prefix)
FROM geolocation
""")

# %%
con.sql("""
WITH zip_coordinates AS (
    SELECT 
        geolocation_zip_code_prefix AS zip_prefix,
        MIN(geolocation_lat) AS min_lat,
        MAX(geolocation_lat) AS max_lat,
        MIN(geolocation_lng) AS min_lng,
        MAX(geolocation_lng) AS max_lng,
        MEDIAN(geolocation_lat) AS median_lat,
        MEDIAN(geolocation_lng) AS median_lng,
        AVG(geolocation_lat) AS avg_lat,
        AVG(geolocation_lng) AS avg_lng,
        (max_lat - min_lat) AS lat_diff,
        (max_lng - min_lng) AS lng_diff,
        ABS(avg_lat - median_lat),
        ABS(avg_lng - median_lng),
    FROM geolocation
    GROUP BY geolocation_zip_code_prefix
)

SELECT 
    *
FROM zip_coordinates
ORDER BY lat_diff DESC, lng_diff DESC;
""")

# %% [markdown]
# Таблица геолокации содержит несколько координат для одного zip-префикса и отдельные экстремальные значения. Для уменьшения влияния выбросов координаты агрегированы медианой. Полученная точка представляет приблизительное местоположение префикса, а не точный адрес.

# %%
con.sql("""
DESCRIBE customers;
""")

# %%
con.sql("""
DESCRIBE sellers;
""")

# %%
con.sql("""
DESCRIBE geolocation;
""")

# %%
con.sql("""
SELECT 
    COUNT(*),
    COUNT(DISTINCT customer_zip_code_prefix) 
FROM customers
""")

# %%
con.sql("""
SELECT 
    COUNT(*),
    COUNT(DISTINCT seller_zip_code_prefix) 
FROM sellers
""")

# %%
con.sql("""
WITH zip_coordinates AS (
    SELECT 
        geolocation_zip_code_prefix AS zip_prefix,
        MEDIAN(geolocation_lat) AS latitude,
        MEDIAN(geolocation_lng) AS longitude,
    FROM geolocation
    GROUP BY geolocation_zip_code_prefix
)
SELECT 
    COUNT(*) customers_count,
    COUNT(*) FILTER (WHERE latitude IS NOT NULL) lat,
    COUNT(*) FILTER (WHERE longitude IS NOT NULL) lng,
    COUNT(*) FILTER (WHERE zc.zip_prefix IS NULL) null_zip_prefix,
    ROUND(null_zip_prefix / customers_count * 100, 2) AS pct_missing
FROM customers c
    LEFT JOIN zip_coordinates zc ON c.customer_zip_code_prefix = zc.zip_prefix
""")

# %%
con.sql("""
WITH zip_coordinates AS (
    SELECT 
        geolocation_zip_code_prefix AS zip_prefix,
        MEDIAN(geolocation_lat) AS latitude,
        MEDIAN(geolocation_lng) AS longitude,
    FROM geolocation
    GROUP BY geolocation_zip_code_prefix
)
SELECT 
    COUNT(*) AS sellers_count,
    COUNT(*) FILTER (WHERE latitude IS NOT NULL) lat,
    COUNT(*) FILTER (WHERE longitude IS NOT NULL) lng,
    COUNT(*) FILTER (WHERE zc.zip_prefix IS NULL) null_zip_prefix,
    ROUND(null_zip_prefix / sellers_count * 100, 2) AS pct_missing
FROM sellers s
    LEFT JOIN zip_coordinates zc ON s.seller_zip_code_prefix = zc.zip_prefix
""")

# %%
con.sql("""
WITH order_sellers AS (
    SELECT 
        order_id,
        seller_id
    FROM order_items
    GROUP BY order_id, seller_id
),
order_seller_count AS (
    SELECT 
        order_id,
        COUNT(seller_id) AS seller_count 
    FROM order_sellers
    GROUP BY order_id
)
SELECT 
    COUNT(*) AS orders_count,
    CASE 
        WHEN seller_count = 1 THEN 'One_seller'
        WHEN seller_count > 1 THEN 'Multiple_sellers'
    ELSE 'Not Found'
    END AS seller_count_group
FROM order_seller_count
GROUP BY seller_count_group
""")

# %%
distance = con.sql("""
WITH order_sellers AS (
    SELECT 
        order_id,
        seller_id
    FROM order_items
    GROUP BY order_id, seller_id
),
order_seller_count AS (
    SELECT
        order_id,
        COUNT(seller_id) AS seller_count
    FROM order_sellers
    GROUP BY order_id
),
zip_coordinates AS (
    SELECT 
        geolocation_zip_code_prefix AS zip_prefix,
        MEDIAN(geolocation_lat) AS latitude,
        MEDIAN(geolocation_lng) AS longitude,
    FROM geolocation
    GROUP BY geolocation_zip_code_prefix
),
route_coordinates AS (
SELECT
    order_id,
    seller_id,
    customers.customer_id,
    customer_state,
    seller_zip_code_prefix,
    customer_zip_code_prefix,
    seller_geo.latitude AS seller_latitude,
    seller_geo.longitude AS seller_longitude,
    customer_geo.latitude AS customer_latitude,
    customer_geo.longitude AS customer_longitude
FROM order_sellers
    JOIN orders USING (order_id)
    JOIN sellers USING (seller_id)
    JOIN customers 
        ON orders.customer_id = customers.customer_id
    JOIN order_seller_count osc USING (order_id)
    LEFT JOIN zip_coordinates seller_geo 
        ON seller_geo.zip_prefix = sellers.seller_zip_code_prefix
    LEFT JOIN zip_coordinates customer_geo 
        ON customer_geo.zip_prefix = customers.customer_zip_code_prefix 
WHERE osc.seller_count = 1
),
coordinates_radians AS ( 
SELECT
    order_id,
    seller_id,
    customer_state,
    seller_latitude,
    seller_longitude,
    customer_latitude,
    customer_longitude,
    RADIANS(seller_latitude) AS seller_lat_rad,
    RADIANS(seller_longitude) AS seller_lng_rad,
    RADIANS(customer_latitude) AS customer_lat_rad,
    RADIANS(customer_longitude) AS customer_lng_rad
FROM route_coordinates rc
WHERE (rc.seller_latitude IS NOT NULL AND rc.customer_latitude IS NOT NULL AND rc.seller_longitude IS NOT NULL AND rc.customer_longitude IS NOT NULL)
),
haversine_components AS (
SELECT
    order_id,
    seller_id,
    customer_state,
    customer_lat_rad - seller_lat_rad AS delta_lat,
    customer_lng_rad - seller_lng_rad AS delta_lng,
    POW(SIN(delta_lat / 2), 2) + COS(seller_lat_rad) * COS(customer_lat_rad) * POW(SIN(delta_lng / 2), 2) AS a
FROM coordinates_radians
ORDER BY a
),
route_distances AS (
SELECT 
    order_id,
    rc.seller_id,
    rc.customer_state,
    seller_zip_code_prefix,
    customer_zip_code_prefix,
    seller_latitude,
    seller_longitude,
    customer_latitude,
    customer_longitude,
    6371 * 2 * ASIN(SQRT(a)) AS distance_km
FROM haversine_components     
    JOIN route_coordinates rc USING (order_id)
)
SELECT distance_km FROM route_distances
ORDER BY distance_km
""").df()

# %%
sns.histplot(distance)

# %%
con.sql("""
CREATE OR REPLACE TEMP VIEW zip_coordinates AS

SELECT 
    geolocation_zip_code_prefix AS zip_prefix,
    geolocation_state as state,
    MEDIAN(geolocation_lat) AS latitude,
    MEDIAN(geolocation_lng) AS longitude,
    MIN(geolocation_lat) AS min_lat,
    MAX(geolocation_lat) AS max_lat,
    MIN(geolocation_lng) AS min_lng,
    MAX(geolocation_lng) AS max_lng,
    AVG(geolocation_lat) AS avg_lat,
    AVG(geolocation_lng) AS avg_lng,
    (max_lat - min_lat) AS lat_diff,
    (max_lng - min_lng) AS lng_diff,
    ABS(avg_lat - latitude) lat_avg_median_diff,
    ABS(avg_lng - longitude) lng_avg_median_diff,

    COUNT(*) as count_coordinates
FROM geolocation
GROUP BY geolocation_zip_code_prefix, geolocation_state
""")

# %%
con.sql("""
SELECT * FROM zip_coordinates
""")

# %%
con.sql("""
CREATE OR REPLACE TEMP VIEW route_distances AS

WITH order_sellers AS (
    SELECT 
        order_id,
        seller_id
    FROM order_items
    GROUP BY order_id, seller_id
),
order_seller_count AS (
    SELECT
        order_id,
        COUNT(seller_id) AS seller_count
    FROM order_sellers
    GROUP BY order_id
),
route_coordinates AS (
SELECT
    order_id,
    sellers.seller_id,
    customers.customer_id,
    customer_state,
    seller_state,
    seller_zip_code_prefix,
    customer_zip_code_prefix,
    seller_geo.latitude AS seller_latitude,
    seller_geo.longitude AS seller_longitude,
    customer_geo.latitude AS customer_latitude,
    customer_geo.longitude AS customer_longitude
FROM order_sellers
    JOIN orders USING (order_id)
    JOIN sellers ON order_sellers.seller_id = sellers.seller_id
    JOIN customers ON orders.customer_id = customers.customer_id
    JOIN order_seller_count osc USING (order_id)
    LEFT JOIN zip_coordinates seller_geo 
        ON seller_geo.zip_prefix = sellers.seller_zip_code_prefix
        AND seller_geo.state = sellers.seller_state
    LEFT JOIN zip_coordinates customer_geo 
        ON customer_geo.zip_prefix = customers.customer_zip_code_prefix 
        AND customer_geo.state = customers.customer_state
WHERE osc.seller_count = 1
),
coordinates_radians AS ( 
SELECT
    order_id,
    seller_id,
    customer_state,
    seller_state,
    seller_latitude,
    seller_longitude,
    customer_latitude,
    customer_longitude,
    RADIANS(seller_latitude) AS seller_lat_rad,
    RADIANS(seller_longitude) AS seller_lng_rad,
    RADIANS(customer_latitude) AS customer_lat_rad,
    RADIANS(customer_longitude) AS customer_lng_rad
FROM route_coordinates rc
WHERE (rc.seller_latitude IS NOT NULL AND rc.customer_latitude IS NOT NULL AND rc.seller_longitude IS NOT NULL AND rc.customer_longitude IS NOT NULL)
),
haversine_components AS (
SELECT
    order_id,
    seller_id,
    seller_state,
    customer_state,
    customer_lat_rad - seller_lat_rad AS delta_lat,
    customer_lng_rad - seller_lng_rad AS delta_lng,
    POW(SIN(delta_lat / 2), 2) + COS(seller_lat_rad) * COS(customer_lat_rad) * POW(SIN(delta_lng / 2), 2) AS a
FROM coordinates_radians
)
SELECT 
    order_id,
    rc.seller_id,
    rc.seller_state,
    rc.customer_state,
    seller_zip_code_prefix,
    customer_zip_code_prefix,
    seller_latitude,
    seller_longitude,
    customer_latitude,
    customer_longitude,
    6371 * 2 * ASIN(SQRT(a)) AS straight_line_distance_km
FROM haversine_components     
    JOIN route_coordinates rc USING (order_id)
""")

# %%
con.sql("""
SELECT COUNT(*), COUNT(DISTINCT order_id)
FROM route_distances
""")

# %%
con.sql("""
SELECT
    QUANTILE_CONT(straight_line_distance_km, 0.8) AS p80,
    QUANTILE_CONT(straight_line_distance_km, 0.9) AS p90,
    QUANTILE_CONT(straight_line_distance_km, 0.95) AS p95,
    QUANTILE_CONT(straight_line_distance_km, 0.99) AS p99,
    QUANTILE_CONT(straight_line_distance_km, 0.999) AS p99_9,
FROM route_distances
""")

# %%
con.sql("""
SELECT 
    customer_state, 
    seller_state, 
    seller_zip_code_prefix, 
    customer_zip_code_prefix, 
    straight_line_distance_km,
    exc_seller.lat_diff as seller_lat_diff, 
    exc_customer.lat_diff as customer_lat_diff, 
    exc_seller.lng_diff as seller_lng_diff,
    exc_customer.lng_diff as customer_lng_diff,
FROM route_distances rc
    LEFT JOIN zip_coordinates exc_seller
        ON rc.seller_zip_code_prefix = exc_seller.zip_prefix
        AND rc.seller_state = exc_seller.state
    LEFT JOIN zip_coordinates exc_customer
        ON rc.customer_zip_code_prefix = exc_customer.zip_prefix
        AND rc.customer_state = exc_customer.state
ORDER BY straight_line_distance_km DESC
LIMIT 20;
""")

# %%
con.sql("""
SELECT 
    COUNT(*),
    MEDIAN(lat_diff) AS median_lat_diff,
    MEDIAN(lng_diff) AS median_lng_diff,
    QUANTILE_CONT(lat_diff, 0.9) AS lat_diff_p90,
    QUANTILE_CONT(lat_diff, 0.95) AS lat_diff_p95,
    QUANTILE_CONT(lat_diff, 0.99) AS lat_diff_p99,
    QUANTILE_CONT(lat_diff, 0.999) AS lat_diff_p999,
    QUANTILE_CONT(lng_diff, 0.9) AS lng_diff_p90,
    QUANTILE_CONT(lng_diff, 0.95) AS lng_diff_p95,
    QUANTILE_CONT(lng_diff, 0.99) AS lng_diff_p99,
    QUANTILE_CONT(lng_diff, 0.999) AS lng_diff_p999,
    MAX(lat_diff),
    MAX(lng_diff)
FROM zip_coordinates
""")

# %%
con.sql("""
WITH zip_tresholds AS ( 
SELECT 
    QUANTILE_CONT(lat_diff, 0.999) AS lat_diff_p999,
    QUANTILE_CONT(lng_diff, 0.999) AS lng_diff_p999,
FROM zip_coordinates
),
zip_quality AS (
SELECT 
    zip_prefix,
    state,
    lat_diff > lat_diff_p999 AS lat_cond,
    lng_diff > lng_diff_p999 AS lng_cond
FROM zip_coordinates
    CROSS JOIN zip_tresholds
)
SELECT
    COUNT(*),
    COUNT(*) FILTER (WHERE lat_cond OR lng_cond),
    COUNT(*) FILTER (WHERE lat_cond AND lng_cond)
FROM zip_quality
""")

# %%
con.sql("""
WITH zip_tresholds AS ( 
SELECT 
    QUANTILE_CONT(lat_diff, 0.999) AS lat_diff_p999,
    QUANTILE_CONT(lng_diff, 0.999) AS lng_diff_p999,
FROM zip_coordinates
),
zip_quality AS (
SELECT 
    zip_prefix,
    state,
    lat_diff > lat_diff_p999 AS lat_cond,
    lng_diff > lng_diff_p999 AS lng_cond
FROM zip_coordinates
    CROSS JOIN zip_tresholds
),
route_zip_quality AS (
SELECT 
    order_id,
    seller_zip_code_prefix,
    seller_state,
    customer_zip_code_prefix,
    customer_state,
    seller_quality.lat_cond AS seller_lat_cond,
    seller_quality.lng_cond AS seller_lng_cond,
    customer_quality.lat_cond AS customer_lat_cond,
    customer_quality.lng_cond AS customer_lng_cond,

FROM route_distances rd
    JOIN zip_quality seller_quality 
        ON rd.seller_zip_code_prefix = seller_quality.zip_prefix
        AND rd.seller_state = seller_quality.state
    JOIN zip_quality customer_quality 
        ON rd.customer_zip_code_prefix = customer_quality.zip_prefix
        AND rd.customer_state = customer_quality.state
),
route_quality_summary AS ( 
SELECT
    COUNT(*) as orders_count,
    COUNT(*) FILTER (WHERE seller_lat_cond OR seller_lng_cond) AS seller_suspicious,
    COUNT(*) FILTER (WHERE customer_lat_cond OR customer_lng_cond) AS customer_suspicious,
    COUNT(*) FILTER (WHERE (seller_lat_cond OR seller_lng_cond) OR (customer_lat_cond OR customer_lng_cond)) AS route_suspicious

FROM route_zip_quality
)
SELECT route_suspicious / orders_count * 100 AS suspicious_pct FROM route_quality_summary
""")

# %%
con.sql("""
WITH zip_tresholds AS ( 
SELECT 
    QUANTILE_CONT(lat_diff, 0.999) AS lat_diff_p999,
    QUANTILE_CONT(lng_diff, 0.999) AS lng_diff_p999,
FROM zip_coordinates
),
zip_quality AS (
SELECT 
    zip_prefix,
    state,
    lat_diff > lat_diff_p999 AS lat_cond,
    lng_diff > lng_diff_p999 AS lng_cond
FROM zip_coordinates
    CROSS JOIN zip_tresholds
),
route_zip_quality AS (
SELECT 
    order_id,
    seller_zip_code_prefix,
    seller_state,
    customer_zip_code_prefix,
    customer_state,
    straight_line_distance_km,
    seller_quality.lat_cond AS seller_lat_cond,
    seller_quality.lng_cond AS seller_lng_cond,
    customer_quality.lat_cond AS customer_lat_cond,
    customer_quality.lng_cond AS customer_lng_cond,
    (
        seller_lat_cond
        OR seller_lng_cond
        OR customer_lat_cond
        OR customer_lng_cond
    ) AS is_suspicious_route

FROM route_distances rd
    JOIN zip_quality seller_quality 
        ON rd.seller_zip_code_prefix = seller_quality.zip_prefix
        AND rd.seller_state = seller_quality.state
    JOIN zip_quality customer_quality 
        ON rd.customer_zip_code_prefix = customer_quality.zip_prefix
        AND rd.customer_state = customer_quality.state
)
SELECT 
    is_suspicious_route,
    COUNT(*),
    AVG(straight_line_distance_km),
    MEDIAN(straight_line_distance_km),
    MIN(straight_line_distance_km),
    MAX(straight_line_distance_km),
    QUANTILE_CONT(straight_line_distance_km, 0.99)
    

FROM route_zip_quality
GROUP BY is_suspicious_route
""")

# %% [markdown]
# #### Вывод: 
# 63 маршрута (0,07%) связаны с ZIP-префиксами, имеющими экстремальный внутренний разброс координат. Эти маршруты в среднем длиннее остальных, однако их исключение практически не изменяет среднее, медиану и 99-й перцентиль расстояния. Максимальное расстояние остаётся аномальным, поскольку фильтр внутреннего разброса не обнаруживает согласованно ошибочные координаты. Поэтому экстремумы следует интерпретировать осторожно, тогда как основные характеристики распределения устойчивы к найденным аномалиям.

# %% [markdown]
# ### Связь расстояния и опоздания RJ

# %%
