-- ====================================================================
-- ApexAnalytics: Cohort Retention Analytics
-- Identifies customer acquisition cohort month based on first order,
-- tracks purchase behavior in subsequent months, and calculates retention %.
-- ====================================================================

WITH customer_first_purchase AS (
    -- Step 1: Find the first purchase date/month for each customer
    SELECT 
        customer_id,
        MIN(order_date) AS first_order_date,
        strftime('%Y-%m', MIN(order_date)) AS cohort_month
    FROM fact_sales
    WHERE status != 'Cancelled'
    GROUP BY customer_id
),

order_months AS (
    -- Step 2: Extract distinct active months of purchase for each customer
    SELECT DISTINCT 
        customer_id,
        strftime('%Y-%m', order_date) AS purchase_month
    FROM fact_sales
    WHERE status != 'Cancelled'
),

cohort_activity AS (
    -- Step 3: Join purchase history back to the cohort details and calculate Month Index
    -- Month Index is the number of months between first order and subsequent order.
    SELECT 
        c.cohort_month,
        o.purchase_month,
        c.customer_id,
        -- Calculate difference in months:
        -- ((Year2 - Year1) * 12) + (Month2 - Month1)
        (
            (CAST(strftime('%Y', o.purchase_month || '-01') AS INTEGER) - CAST(strftime('%Y', c.cohort_month || '-01') AS INTEGER)) * 12
        ) + (
            CAST(strftime('%m', o.purchase_month || '-01') AS INTEGER) - CAST(strftime('%m', c.cohort_month || '-01') AS INTEGER)
        ) AS month_index
    FROM order_months o
    JOIN customer_first_purchase c ON o.customer_id = c.customer_id
),

cohort_sizes AS (
    -- Step 4: Count the total unique customers in each cohort (Cohort Size)
    SELECT 
        cohort_month,
        COUNT(DISTINCT customer_id) AS cohort_size
    FROM customer_first_purchase
    GROUP BY cohort_month
),

retention_counts AS (
    -- Step 5: Aggregate active customers by cohort month and month index
    SELECT 
        cohort_month,
        month_index,
        COUNT(DISTINCT customer_id) AS active_customers
    FROM cohort_activity
    GROUP BY cohort_month, month_index
)

-- Step 6: Final calculation - join everything to compute retention %
SELECT 
    r.cohort_month,
    s.cohort_size,
    r.month_index,
    r.active_customers,
    ROUND((r.active_customers * 100.0) / s.cohort_size, 2) AS retention_percentage
FROM retention_counts r
JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
ORDER BY r.cohort_month ASC, r.month_index ASC;
