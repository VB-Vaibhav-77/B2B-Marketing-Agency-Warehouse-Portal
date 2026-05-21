-- ==========================================
-- ApexAnalytics: Relational Schema DDL (Galaxy Schema)
-- Designed for SQLite & fully standard SQL (BigQuery-friendly)
-- ==========================================

-- Drop existing tables to ensure a clean run
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS fact_web_traffic;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_date;

-- 1. Create Customer Dimension Table
CREATE TABLE dim_customers (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT,
    country TEXT,
    signup_date TEXT NOT NULL
);

-- 2. Create Product Dimension Table
CREATE TABLE dim_products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    base_price REAL NOT NULL
);

-- 3. Create Date Dimension Table
CREATE TABLE dim_date (
    date_key TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    quarter_name TEXT NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    month_short TEXT NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL
);

-- 4. Create Sales Fact Table
CREATE TABLE fact_sales (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    line_subtotal REAL NOT NULL,
    shipping_fee REAL NOT NULL,
    status TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id),
    FOREIGN KEY (order_date) REFERENCES dim_date(date_key)
);

-- 5. Create Web Traffic Fact Table
CREATE TABLE fact_web_traffic (
    session_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    session_date TEXT NOT NULL,
    traffic_source TEXT NOT NULL,
    device_type TEXT NOT NULL,
    pages_viewed INTEGER NOT NULL,
    duration_seconds INTEGER NOT NULL,
    bounced INTEGER NOT NULL,
    converted INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
    FOREIGN KEY (session_date) REFERENCES dim_date(date_key)
);

-- ==========================================
-- PERFORMANCE INDEXING LAYER
-- Indexes created on joining keys for massive query speedups in fact-to-dimension relationships
-- ==========================================
CREATE INDEX idx_sales_customer ON fact_sales(customer_id);
CREATE INDEX idx_sales_product ON fact_sales(product_id);
CREATE INDEX idx_sales_date ON fact_sales(order_date);
CREATE INDEX idx_web_customer ON fact_web_traffic(customer_id);
CREATE INDEX idx_web_date ON fact_web_traffic(session_date);
CREATE INDEX idx_customers_signup ON dim_customers(signup_date);
