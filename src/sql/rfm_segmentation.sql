-- ====================================================================
-- ApexAnalytics: Advanced Customer RFM Segmentation
-- Computes Recency, Frequency, and Monetary metrics for all customers,
-- ranks them into quintiles (1-5), and classifies them into marketing tiers.
-- ====================================================================

WITH customer_orders AS (
    -- Step 1: Calculate raw RFM metrics per customer
    -- We assume the 'current date' for recency calculation is the day after the last order in the dataset.
    SELECT 
        customer_id,
        MAX(order_date) AS last_purchase_date,
        -- SQLite JulianDay represents days since Epoch
        CAST(JulianDay((SELECT MAX(order_date) FROM fact_sales) || ' 23:59:59') - JulianDay(MAX(order_date)) AS INTEGER) AS recency_days,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(line_subtotal) AS monetary_value
    FROM fact_sales
    WHERE status != 'Cancelled'  -- Exclude cancelled orders from RFM value
    GROUP BY customer_id
),

rfm_scores AS (
    -- Step 2: Bin customers into quintiles (1 to 5) using NTILE.
    -- Recency: Shorter days are BETTER (R=5 is most recent, R=1 is oldest)
    -- Frequency: Larger numbers are BETTER (F=5 is highest frequency, F=1 is lowest)
    -- Monetary: Larger spend is BETTER (M=5 is highest spend, M=1 is lowest)
    SELECT 
        customer_id,
        recency_days,
        frequency,
        monetary_value,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score, -- Note DESC because lower recency days = better rank
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary_value ASC) AS m_score
    FROM customer_orders
),

customer_segmentation AS (
    -- Step 3: Segment customers based on R and F scores (standard RFM grid logic)
    SELECT 
        r.customer_id,
        c.full_name,
        c.email,
        c.country,
        r.recency_days,
        r.frequency,
        r.monetary_value,
        r.r_score,
        r.f_score,
        r.m_score,
        (r.r_score + r.f_score + r.m_score) / 3.0 AS average_rfm_score,
        CASE
            WHEN r.r_score >= 4 AND r.f_score >= 4 THEN 'Champions'
            WHEN r.r_score >= 3 AND r.f_score >= 3 THEN 'Loyal Customers'
            WHEN r.r_score >= 4 AND r.f_score = 2 THEN 'Promising'
            WHEN r.r_score = 3 AND r.f_score = 2 THEN 'Need Attention'
            WHEN r.r_score >= 4 AND r.f_score = 1 THEN 'New Customers'
            WHEN r.r_score <= 2 AND r.f_score >= 4 THEN 'Cannot Lose Them'
            WHEN r.r_score <= 2 AND r.f_score = 3 THEN 'At Risk'
            WHEN r.r_score = 2 AND r.f_score <= 2 THEN 'About to Sleep'
            ELSE 'Lost / Inactive'
        END AS rfm_segment
    FROM rfm_scores r
    JOIN dim_customers c ON r.customer_id = c.customer_id
)

-- Final Select: Return sorted data ready for reporting
SELECT 
    customer_id,
    full_name,
    email,
    country,
    recency_days,
    frequency,
    monetary_value,
    r_score,
    f_score,
    m_score,
    average_rfm_score,
    rfm_segment
FROM customer_segmentation
ORDER BY monetary_value DESC;
