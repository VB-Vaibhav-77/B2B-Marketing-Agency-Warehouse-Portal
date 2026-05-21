-- ====================================================================
-- ApexAnalytics: Advanced E-Commerce Marketing Attribution Analysis
-- Performs Last-Touch Attribution by mapping orders in fact_sales to the 
-- highest-engagement web session (fact_web_traffic) on the exact order date
-- for each customer, calculating conversion rates and ROI per traffic source.
-- ====================================================================

WITH session_ranking AS (
    -- Step 1: Rank sessions for each customer on each day to select the "best" touchpoint.
    -- If a customer has multiple sessions in a day, we prioritize the one with the longest duration
    -- and highest number of page views.
    SELECT 
        session_id,
        customer_id,
        session_date,
        traffic_source,
        device_type,
        pages_viewed,
        duration_seconds,
        bounced,
        converted,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id, session_date 
            ORDER BY duration_seconds DESC, pages_viewed DESC
        ) AS session_rank
    FROM fact_web_traffic
),

best_daily_sessions AS (
    -- Step 2: Extract exactly one primary session per customer, per day
    SELECT 
        session_id,
        customer_id,
        session_date,
        traffic_source,
        device_type,
        pages_viewed,
        duration_seconds,
        bounced,
        converted
    FROM session_ranking
    WHERE session_rank = 1
),

attributed_sales AS (
    -- Step 3: Join completed orders to daily sessions for multi-fact attribution
    SELECT 
        s.order_item_id,
        s.order_id,
        s.customer_id,
        s.product_id,
        s.order_date,
        s.quantity,
        s.unit_price,
        s.line_subtotal,
        s.shipping_fee,
        COALESCE(sess.traffic_source, 'Direct/Unattributed') AS attributed_source,
        COALESCE(sess.device_type, 'Unknown') AS attributed_device
    FROM fact_sales s
    LEFT JOIN best_daily_sessions sess 
      ON s.customer_id = sess.customer_id 
     AND s.order_date = sess.session_date
    WHERE s.status != 'Cancelled'
),

channel_traffic_metrics AS (
    -- Step 4: Aggregate traffic and engagement facts by source channel
    SELECT 
        traffic_source,
        COUNT(session_id) AS total_sessions,
        SUM(bounced) AS bounced_sessions,
        SUM(converted) AS converted_sessions,
        CAST(SUM(bounced) AS REAL) / COUNT(session_id) AS bounce_rate,
        CAST(SUM(converted) AS REAL) / COUNT(session_id) AS session_conversion_rate
    FROM fact_web_traffic
    GROUP BY traffic_source
),

channel_sales_metrics AS (
    -- Step 5: Aggregate financial facts by attributed channel
    SELECT 
        attributed_source,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(quantity) AS total_units_sold,
        SUM(line_subtotal) AS gross_revenue,
        SUM(shipping_fee) AS total_shipping_revenue
    FROM attributed_sales
    GROUP BY attributed_source
)

-- Step 6: Combine traffic and financial metrics to compute ROI & Channel Efficiency
SELECT 
    t.traffic_source,
    t.total_sessions,
    t.bounced_sessions,
    ROUND(t.bounce_rate * 100, 2) AS bounce_rate_pct,
    ROUND(t.session_conversion_rate * 100, 2) AS session_conversion_rate_pct,
    COALESCE(s.total_orders, 0) AS total_orders,
    COALESCE(s.total_units_sold, 0) AS units_sold,
    ROUND(COALESCE(s.gross_revenue, 0), 2) AS gross_revenue,
    ROUND(COALESCE(s.gross_revenue, 0) / t.total_sessions, 2) AS revenue_per_session,
    ROUND(COALESCE(s.gross_revenue, 0) / COALESCE(s.total_orders, 1), 2) AS average_order_value
FROM channel_traffic_metrics t
LEFT JOIN channel_sales_metrics s 
  ON t.traffic_source = s.attributed_source
ORDER BY gross_revenue DESC;
