import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ETL_Pipeline")

class EcomETL:
    def __init__(self, raw_data_dir="data/raw", processed_data_dir="data/processed"):
        self.raw_dir = raw_data_dir
        self.processed_dir = processed_data_dir
        os.makedirs(self.processed_dir, exist_ok=True)
        
        # Output paths
        self.cust_raw_path = os.path.join(self.raw_dir, "customers_raw.csv")
        self.prod_raw_path = os.path.join(self.raw_dir, "products_raw.csv")
        self.ord_raw_path = os.path.join(self.raw_dir, "orders_raw.csv")
        self.items_raw_path = os.path.join(self.raw_dir, "order_items_raw.csv")
        self.sess_raw_path = os.path.join(self.raw_dir, "sessions_raw.csv")
        
        # Clean Dataframes
        self.dim_customers = None
        self.dim_products = None
        self.dim_date = None
        self.fact_sales = None
        self.fact_web_traffic = None

    def run_pipeline(self):
        logger.info("Starting ApexAnalytics ETL Pipeline execution...")
        
        # 1. EXTRACT
        cust_raw, prod_raw, ord_raw, items_raw, sess_raw = self.extract_data()
        
        # 2. TRANSFORM & MODEL STAR/GALAXY SCHEMA
        self.transform_data(cust_raw, prod_raw, ord_raw, items_raw, sess_raw)
        
        # 3. EXPORT CLEAN FILES (CSVs)
        self.save_processed_data()
        
        logger.info("ETL Pipeline finished successfully!")

    def extract_data(self):
        logger.info("Phase 1: Extracting raw CSV files...")
        
        # Check files existence
        required_paths = [self.cust_raw_path, self.prod_raw_path, self.ord_raw_path, self.items_raw_path, self.sess_raw_path]
        for p in required_paths:
            if not os.path.exists(p):
                raise FileNotFoundError(f"Missing raw data file: {p}. Run raw data generator first!")
                
        cust = pd.read_csv(self.cust_raw_path)
        prod = pd.read_csv(self.prod_raw_path)
        ord_df = pd.read_csv(self.ord_raw_path)
        items = pd.read_csv(self.items_raw_path)
        sess = pd.read_csv(self.sess_raw_path)
        
        logger.info(f"Successfully loaded raw datasets:")
        logger.info(f" - Customers: {cust.shape[0]} rows")
        logger.info(f" - Products: {prod.shape[0]} rows")
        logger.info(f" - Orders: {ord_df.shape[0]} rows")
        logger.info(f" - Order Items: {items.shape[0]} rows")
        logger.info(f" - Website Sessions: {sess.shape[0]} rows")
        
        return cust, prod, ord_df, items, sess

    def _parse_dates_flexibly(self, date_series):
        """Converts date series to datetime, supporting mixed formats and handling errors gracefully."""
        parsed = pd.to_datetime(date_series, errors='coerce', format='mixed')
        return parsed

    def transform_data(self, cust_raw, prod_raw, ord_raw, items_raw, sess_raw):
        logger.info("Phase 2: Transforming and Modeling data...")
        
        # ----------------------------------------------------
        # A. TRANSFORM PRODUCTS -> dim_products
        # ----------------------------------------------------
        logger.info("Building [dim_products]...")
        prod_clean = prod_raw.copy()
        
        # Clean price outliers and negative pricing anomalies
        invalid_prices = prod_clean[(prod_clean['base_price'] <= 0) | (prod_clean['base_price'] > 5000)]
        logger.info(f" - Filtering out {len(invalid_prices)} product anomalies (prices <= $0 or > $5,000)")
        prod_clean = prod_clean[(prod_clean['base_price'] > 0) & (prod_clean['base_price'] <= 5000)]
        
        # Fill missing product names or categories
        prod_clean['product_name'] = prod_clean['product_name'].fillna('Unknown Product').str.strip()
        prod_clean['category'] = prod_clean['category'].fillna('General').str.strip()
        
        self.dim_products = prod_clean.reset_index(drop=True)
        logger.info(f" - dim_products created: {self.dim_products.shape[0]} rows")
        
        # ----------------------------------------------------
        # B. TRANSFORM CUSTOMERS -> dim_customers
        # ----------------------------------------------------
        logger.info("Building [dim_customers]...")
        cust_clean = cust_raw.copy()
        
        # Deduplication based on customer_id
        duplicates = cust_clean.duplicated(subset=['customer_id'], keep='first').sum()
        logger.info(f" - Deduplicating customers: removing {duplicates} duplicate IDs")
        cust_clean = cust_clean.drop_duplicates(subset=['customer_id'], keep='first')
        
        # Clean names
        cust_clean['full_name'] = cust_clean['full_name'].fillna('Missing Name')
        cust_clean['full_name'] = cust_clean['full_name'].str.strip().str.title()
        
        # Clean Emails
        cust_clean['email'] = cust_clean['email'].fillna('no-email@apexgoods.com').str.strip().str.lower()
        
        # Standardize Country values
        country_mapping = {
            "US": "United States",
            "USA": "United States",
            "US of A": "United States",
            "UK": "United Kingdom",
            "U.K.": "United Kingdom"
        }
        cust_clean['country'] = cust_clean['country'].fillna('Unknown').str.strip()
        cust_clean['country'] = cust_clean['country'].replace(country_mapping)
        
        # Flexible Date Parsing
        cust_clean['signup_date'] = self._parse_dates_flexibly(cust_clean['signup_date'])
        
        # Filter out-of-bounds dates (e.g. year 0202)
        out_of_bounds = (cust_clean['signup_date'] < pd.Timestamp('2020-01-01')) | (cust_clean['signup_date'] > pd.Timestamp('2027-12-31'))
        cust_clean.loc[out_of_bounds, 'signup_date'] = pd.NaT
        
        # Handle Null/Corrupt signup dates
        null_dates = cust_clean['signup_date'].isna().sum()
        logger.info(f" - Standardizing signup dates: resolved {null_dates} null/corrupt signup dates")
        cust_clean['signup_date'] = cust_clean['signup_date'].fillna(pd.Timestamp('2024-01-01'))
        
        self.dim_customers = cust_clean[['customer_id', 'full_name', 'email', 'country', 'signup_date']].reset_index(drop=True)
        logger.info(f" - dim_customers created: {self.dim_customers.shape[0]} rows")
        
        # ----------------------------------------------------
        # C. TRANSFORM ORDERS & ORDER ITEMS -> fact_sales (Fact #1)
        # ----------------------------------------------------
        logger.info("Building [fact_sales]...")
        ord_clean = ord_raw.copy()
        items_clean = items_raw.copy()
        
        # Deduplicate orders
        dup_orders = ord_clean.duplicated(subset=['order_id'], keep='first').sum()
        logger.info(f" - Deduplicating orders: removing {dup_orders} duplicate order entries")
        ord_clean = ord_clean.drop_duplicates(subset=['order_id'], keep='first')
        
        # Parse order dates
        ord_clean['order_date'] = self._parse_dates_flexibly(ord_clean['order_date'])
        out_of_bounds_orders = (ord_clean['order_date'] < pd.Timestamp('2020-01-01')) | (ord_clean['order_date'] > pd.Timestamp('2027-12-31'))
        ord_clean.loc[out_of_bounds_orders, 'order_date'] = pd.NaT
        
        null_order_dates = ord_clean['order_date'].isna().sum()
        if null_order_dates > 0:
            logger.info(f" - Found {null_order_dates} orders with corrupt or out-of-bounds dates. Dropping.")
            ord_clean = ord_clean.dropna(subset=['order_date'])
        
        # Filter Order Items anomalies
        invalid_items = items_clean[(items_clean['quantity'] <= 0) | (items_clean['unit_price'] <= 0)]
        logger.info(f" - Filtering out {len(invalid_items)} order item anomalies (quantity <= 0 or price <= 0)")
        items_clean = items_clean[(items_clean['quantity'] > 0) & (items_clean['unit_price'] > 0)]
        
        # Ensure products exist
        valid_prod_ids = self.dim_products['product_id'].tolist()
        missing_prods = ~items_clean['product_id'].isin(valid_prod_ids)
        if missing_prods.sum() > 0:
            logger.info(f" - Filtering {missing_prods.sum()} order items containing deleted product references")
            items_clean = items_clean[~missing_prods]
            
        # Ensure customer exists
        valid_cust_ids = self.dim_customers['customer_id'].tolist()
        missing_custs = ~ord_clean['customer_id'].isin(valid_cust_ids)
        if missing_custs.sum() > 0:
            logger.info(f" - Filtering {missing_custs.sum()} orders containing non-existent customer IDs")
            ord_clean = ord_clean[~missing_custs]
            
        # Merge orders and order items
        fact_merged = pd.merge(items_clean, ord_clean, on='order_id', how='inner')
        fact_merged['line_subtotal'] = fact_merged['quantity'] * fact_merged['unit_price']
        fact_merged['status'] = fact_merged['status'].fillna('Completed').str.strip().str.capitalize()
        
        # Generate Sales Month Index (precalculated cohort offset for SQL cohort matrix fallback)
        # To make things dynamic, we can join first signup dates to fact table
        cust_signups = self.dim_customers[['customer_id', 'signup_date']]
        fact_merged = pd.merge(fact_merged, cust_signups, on='customer_id', how='inner')
        # Difference in months: (Yr2 - Yr1) * 12 + (Mo2 - Mo1)
        fact_merged['month_index'] = (
            (fact_merged['order_date'].dt.year - fact_merged['signup_date'].dt.year) * 12 + 
            (fact_merged['order_date'].dt.month - fact_merged['signup_date'].dt.month)
        )
        # Cap index at 0 if date mismatch occurs due to clean dates fallback
        fact_merged['month_index'] = fact_merged['month_index'].clip(lower=0)
        
        # Structure the fact table
        self.fact_sales = fact_merged[[
            'order_item_id', 'order_id', 'customer_id', 'product_id', 
            'order_date', 'quantity', 'unit_price', 'line_subtotal', 
            'shipping_fee', 'status', 'month_index'
        ]].reset_index(drop=True)
        
        logger.info(f" - fact_sales created: {self.fact_sales.shape[0]} transaction items")

        # ----------------------------------------------------
        # D. TRANSFORM WEB SESSIONS -> fact_web_traffic (Fact #2)
        # ----------------------------------------------------
        logger.info("Building [fact_web_traffic]...")
        sess_clean = sess_raw.copy()
        
        # Parse session dates
        sess_clean['session_date'] = self._parse_dates_flexibly(sess_clean['session_date'])
        out_of_bounds_sess = (sess_clean['session_date'] < pd.Timestamp('2020-01-01')) | (sess_clean['session_date'] > pd.Timestamp('2027-12-31'))
        sess_clean.loc[out_of_bounds_sess, 'session_date'] = pd.NaT
        
        null_sess_dates = sess_clean['session_date'].isna().sum()
        if null_sess_dates > 0:
            logger.info(f" - Found {null_sess_dates} sessions with corrupt/out-of-bounds dates. Dropping.")
            sess_clean = sess_clean.dropna(subset=['session_date'])
            
        # Clean duration and pages viewed anomalies (must be positive)
        invalid_sess_metrics = sess_clean[(sess_clean['pages_viewed'] <= 0) | (sess_clean['duration_seconds'] < 0)]
        logger.info(f" - Filtering out {len(invalid_sess_metrics)} session entries with negative durations or <= 0 pages.")
        sess_clean = sess_clean[(sess_clean['pages_viewed'] > 0) & (sess_clean['duration_seconds'] >= 0)]
        
        # Ensure referential integrity (customer exists)
        missing_sess_custs = ~sess_clean['customer_id'].isin(valid_cust_ids)
        if missing_sess_custs.sum() > 0:
            logger.info(f" - Filtering {missing_sess_custs.sum()} sessions containing non-existent customer IDs")
            sess_clean = sess_clean[~missing_sess_custs]
            
        # Standardize strings
        sess_clean['traffic_source'] = sess_clean['traffic_source'].fillna('Organic').str.strip()
        sess_clean['device_type'] = sess_clean['device_type'].fillna('Desktop').str.strip()
        
        # Structure second fact table
        self.fact_web_traffic = sess_clean[[
            'session_id', 'customer_id', 'session_date', 'traffic_source', 
            'device_type', 'pages_viewed', 'duration_seconds', 'bounced', 'converted'
        ]].reset_index(drop=True)
        
        logger.info(f" - fact_web_traffic created: {self.fact_web_traffic.shape[0]} sessions")
        
        # ----------------------------------------------------
        # E. BUILD dim_date (Shared Calendar Dimension)
        # ----------------------------------------------------
        logger.info("Building [dim_date]...")
        
        # Find min/max dates across ALL three files (signups, sales orders, web sessions)
        min_date = min(
            self.dim_customers['signup_date'].min(), 
            self.fact_sales['order_date'].min(),
            self.fact_web_traffic['session_date'].min()
        )
        max_date = max(
            self.dim_customers['signup_date'].max(), 
            self.fact_sales['order_date'].max(),
            self.fact_web_traffic['session_date'].max()
        )
        
        # Safe default fallback for empty datasets/unit tests
        if pd.isna(min_date) or pd.isna(max_date):
            logger.warning(" - No valid dates found in datasets. Defaulting calendar to standard bounds.")
            min_date = pd.Timestamp('2024-01-01')
            max_date = pd.Timestamp('2026-12-31')
            
        logger.info(f" - Calendar boundaries: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
        
        # Generate full date range
        date_range = pd.date_range(start=min_date - pd.Timedelta(days=5), end=max_date + pd.Timedelta(days=5))
        
        date_df = pd.DataFrame({'date': date_range})
        date_df['date_key'] = date_df['date'].dt.strftime('%Y-%m-%d')
        date_df['year'] = date_df['date'].dt.year
        date_df['quarter'] = date_df['date'].dt.quarter
        date_df['quarter_name'] = "Q" + date_df['quarter'].astype(str)
        date_df['month'] = date_df['date'].dt.month
        date_df['month_name'] = date_df['date'].dt.strftime('%B')
        date_df['month_short'] = date_df['date'].dt.strftime('%b')
        date_df['day'] = date_df['date'].dt.day
        date_df['day_of_week'] = date_df['date'].dt.dayofweek + 1  # 1-7 (Mon-Sun)
        date_df['day_name'] = date_df['date'].dt.strftime('%A')
        date_df['is_weekend'] = date_df['day_of_week'].isin([6, 7]).astype(int)
        
        self.dim_date = date_df.reset_index(drop=True)
        logger.info(f" - dim_date created: {self.dim_date.shape[0]} dates calendar rows")

    def save_processed_data(self):
        logger.info("Phase 3: Saving cleaned tables to CSV in processed folder...")
        
        # Convert date columns back to string YYYY-MM-DD
        self.dim_customers['signup_date'] = self.dim_customers['signup_date'].dt.strftime('%Y-%m-%d')
        self.fact_sales['order_date'] = self.fact_sales['order_date'].dt.strftime('%Y-%m-%d')
        self.fact_web_traffic['session_date'] = self.fact_web_traffic['session_date'].dt.strftime('%Y-%m-%d')
        
        # Export
        self.dim_customers.to_csv(os.path.join(self.processed_dir, "dim_customers.csv"), index=False)
        self.dim_products.to_csv(os.path.join(self.processed_dir, "dim_products.csv"), index=False)
        self.dim_date.to_csv(os.path.join(self.processed_dir, "dim_date.csv"), index=False)
        self.fact_sales.to_csv(os.path.join(self.processed_dir, "fact_sales.csv"), index=False)
        self.fact_web_traffic.to_csv(os.path.join(self.processed_dir, "fact_web_traffic.csv"), index=False)
        
        logger.info("All star schema tables saved successfully to disk.")

if __name__ == "__main__":
    # Standard raw extract fallback for running file standalone
    cust = pd.read_csv("data/raw/customers_raw.csv")
    prod = pd.read_csv("data/raw/products_raw.csv")
    ord_df = pd.read_csv("data/raw/orders_raw.csv")
    items = pd.read_csv("data/raw/order_items_raw.csv")
    sess = pd.read_csv("data/raw/sessions_raw.csv")
    
    pipeline = EcomETL()
    pipeline.transform_data(cust, prod, ord_df, items, sess)
    pipeline.save_processed_data()
