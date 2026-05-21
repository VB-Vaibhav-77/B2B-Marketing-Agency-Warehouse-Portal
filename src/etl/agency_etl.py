import os
import sqlite3
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("Agency_ETL")

class AgencyPipeline:
    def __init__(self, raw_dir="data/raw_agency", processed_dir="data/processed_agency", db_path="data/agency_analytics.db"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.db_path = db_path
        
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def run_etl(self):
        logger.info("=== STARTING B2B AGENCY ETL PIPELINE ===")
        
        # 1. READ RAW DATA
        logger.info("Reading raw B2B agency CSVs...")
        df_clients = pd.read_csv(os.path.join(self.raw_dir, "clients.csv"))
        df_campaigns = pd.read_csv(os.path.join(self.raw_dir, "campaigns.csv"))
        df_managers = pd.read_csv(os.path.join(self.raw_dir, "managers.csv"))
        df_ad_perf = pd.read_csv(os.path.join(self.raw_dir, "ad_performance.csv"))
        df_billing = pd.read_csv(os.path.join(self.raw_dir, "client_billing.csv"))
        
        # 2. TRANSFORM DATA & DIMENSIONAL MODELING
        logger.info("Modeling dimensions and facts...")
        
        # Clean Clients
        df_clients["company_name"] = df_clients["company_name"].str.strip().str.title()
        df_clients["industry"] = df_clients["industry"].str.strip()
        
        # Clean Managers
        df_managers["name"] = df_managers["name"].str.strip().str.title()
        
        # Generate rich Calendar Dimension (dim_date)
        all_dates = pd.to_datetime(df_ad_perf["date"]).unique()
        df_date = pd.DataFrame({"date_key": all_dates})
        df_date["date_key"] = df_date["date_key"].dt.strftime("%Y-%m-%d")
        df_date = df_date.sort_values("date_key").reset_index(drop=True)
        
        df_date_parsed = pd.to_datetime(df_date["date_key"])
        df_date["year"] = df_date_parsed.dt.year
        df_date["month"] = df_date_parsed.dt.month
        df_date["month_name"] = df_date_parsed.dt.strftime("%B")
        df_date["quarter"] = df_date_parsed.dt.quarter.apply(lambda q: f"Q{q}")
        df_date["day_of_week"] = df_date_parsed.dt.strftime("%A")
        df_date["is_weekend"] = df_date_parsed.dt.weekday.apply(lambda d: 1 if d >= 5 else 0)
        
        # 3. EXPORT CLEAN TABLES
        logger.info("Exporting clean star schema CSV files...")
        df_clients.to_csv(os.path.join(self.processed_dir, "dim_clients.csv"), index=False)
        df_campaigns.to_csv(os.path.join(self.processed_dir, "dim_campaigns.csv"), index=False)
        df_managers.to_csv(os.path.join(self.processed_dir, "dim_account_managers.csv"), index=False)
        df_date.to_csv(os.path.join(self.processed_dir, "dim_date.csv"), index=False)
        df_ad_perf.to_csv(os.path.join(self.processed_dir, "fact_ad_performance.csv"), index=False)
        df_billing.to_csv(os.path.join(self.processed_dir, "fact_client_billing.csv"), index=False)
        
        # 4. LOAD INTO SQLITE DATABASE
        logger.info(f"Loading tables into SQLite database at {self.db_path}...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create Schemas & Tables
            cursor.execute("DROP TABLE IF EXISTS dim_clients;")
            cursor.execute("DROP TABLE IF EXISTS dim_campaigns;")
            cursor.execute("DROP TABLE IF EXISTS dim_account_managers;")
            cursor.execute("DROP TABLE IF EXISTS dim_date;")
            cursor.execute("DROP TABLE IF EXISTS fact_ad_performance;")
            cursor.execute("DROP TABLE IF EXISTS fact_client_billing;")
            
            cursor.execute("""
                CREATE TABLE dim_account_managers (
                    manager_id TEXT PRIMARY KEY,
                    name TEXT,
                    region TEXT,
                    target_monthly_revenue REAL
                );
            """)
            cursor.execute("""
                CREATE TABLE dim_clients (
                    client_id TEXT PRIMARY KEY,
                    company_name TEXT,
                    industry TEXT,
                    client_tier TEXT,
                    monthly_retainer_fee REAL,
                    onboarding_date TEXT,
                    primary_account_manager_id TEXT,
                    FOREIGN KEY (primary_account_manager_id) REFERENCES dim_account_managers(manager_id)
                );
            """)
            cursor.execute("""
                CREATE TABLE dim_campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    client_id TEXT,
                    campaign_name TEXT,
                    marketing_channel TEXT,
                    monthly_ad_budget REAL,
                    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id)
                );
            """)
            cursor.execute("""
                CREATE TABLE dim_date (
                    date_key TEXT PRIMARY KEY,
                    year INTEGER,
                    month INTEGER,
                    month_name TEXT,
                    quarter TEXT,
                    day_of_week TEXT,
                    is_weekend INTEGER
                );
            """)
            cursor.execute("""
                CREATE TABLE fact_ad_performance (
                    date TEXT,
                    campaign_id TEXT,
                    client_id TEXT,
                    ad_spend REAL,
                    impressions INTEGER,
                    clicks INTEGER,
                    conversions INTEGER,
                    client_conversion_revenue REAL,
                    FOREIGN KEY (date) REFERENCES dim_date(date_key),
                    FOREIGN KEY (campaign_id) REFERENCES dim_campaigns(campaign_id),
                    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id)
                );
            """)
            cursor.execute("""
                CREATE TABLE fact_client_billing (
                    invoice_date TEXT,
                    invoice_id TEXT PRIMARY KEY,
                    client_id TEXT,
                    manager_id TEXT,
                    retainer_billing REAL,
                    ad_management_markup REAL,
                    consulting_billing REAL,
                    total_billing_amount REAL,
                    FOREIGN KEY (invoice_date) REFERENCES dim_date(date_key),
                    FOREIGN KEY (client_id) REFERENCES dim_clients(client_id),
                    FOREIGN KEY (manager_id) REFERENCES dim_account_managers(manager_id)
                );
            """)
            
            conn.commit()
            
            # Load Data
            df_managers.to_sql("dim_account_managers", conn, if_exists="append", index=False)
            df_clients.to_sql("dim_clients", conn, if_exists="append", index=False)
            df_campaigns.to_sql("dim_campaigns", conn, if_exists="append", index=False)
            df_date.to_sql("dim_date", conn, if_exists="append", index=False)
            df_ad_perf.to_sql("fact_ad_performance", conn, if_exists="append", index=False)
            df_billing.to_sql("fact_client_billing", conn, if_exists="append", index=False)
            
            # Compile Performance indexes
            cursor.execute("CREATE INDEX idx_ad_perf_client ON fact_ad_performance(client_id);")
            cursor.execute("CREATE INDEX idx_billing_client ON fact_client_billing(client_id);")
            cursor.execute("CREATE INDEX idx_billing_manager ON fact_client_billing(manager_id);")
            conn.commit()
            
            logger.info("[SUCCESS] SQLite database initialized and indexed successfully!")
            
            # 5. EXECUTE ADVANCED SQL QUERIES & EXPORT
            logger.info("Executing Advanced B2B SQL Analytics...")
            
            # Query 1: Account Manager Portfolio Leaderboard
            sql_manager = """
                WITH manager_billing AS (
                    SELECT 
                        c.primary_account_manager_id AS manager_id,
                        COUNT(DISTINCT c.client_id) AS active_clients,
                        SUM(b.total_billing_amount) AS total_billing_managed,
                        SUM(b.total_billing_amount) / COUNT(DISTINCT strftime('%Y-%m', b.invoice_date)) AS avg_monthly_billing
                    FROM dim_clients c
                    LEFT JOIN fact_client_billing b ON c.client_id = b.client_id
                    GROUP BY c.primary_account_manager_id
                ),
                manager_perf AS (
                    SELECT 
                        c.primary_account_manager_id AS manager_id,
                        SUM(a.ad_spend) AS client_ad_spend_managed,
                        SUM(a.client_conversion_revenue) AS client_conversion_revenue_generated
                    FROM dim_clients c
                    LEFT JOIN fact_ad_performance a ON c.client_id = a.client_id
                    GROUP BY c.primary_account_manager_id
                )
                SELECT 
                    m.manager_id,
                    m.name AS manager_name,
                    m.region,
                    m.target_monthly_revenue AS monthly_revenue_target,
                    COALESCE(mb.active_clients, 0) AS active_clients,
                    ROUND(COALESCE(mb.total_billing_managed, 0), 2) AS total_billing_managed,
                    ROUND(COALESCE(mb.avg_monthly_billing, 0), 2) AS avg_monthly_billing,
                    ROUND(COALESCE(mp.client_ad_spend_managed, 0), 2) AS client_ad_spend_managed,
                    ROUND(COALESCE(mp.client_conversion_revenue_generated, 0), 2) AS client_conversion_revenue_generated,
                    ROUND(CASE 
                        WHEN COALESCE(mp.client_ad_spend_managed, 0) > 0 
                        THEN COALESCE(mp.client_conversion_revenue_generated, 0) / COALESCE(mp.client_ad_spend_managed, 0)
                        ELSE 0 
                    END, 2) AS overall_managed_roas
                FROM dim_account_managers m
                LEFT JOIN manager_billing mb ON m.manager_id = mb.manager_id
                LEFT JOIN manager_perf mp ON m.manager_id = mp.manager_id
                ORDER BY total_billing_managed DESC;
            """
            
            # Query 2: Marketing Campaign & Channel Efficiency Grid
            sql_channel = """
                SELECT 
                    cp.marketing_channel,
                    COUNT(DISTINCT cp.campaign_id) AS total_campaigns,
                    ROUND(SUM(ap.ad_spend), 2) AS total_ad_spend,
                    SUM(ap.impressions) AS total_impressions,
                    SUM(ap.clicks) AS total_clicks,
                    SUM(ap.conversions) AS total_conversions,
                    ROUND(SUM(ap.client_conversion_revenue), 2) AS conversion_revenue,
                    ROUND((SUM(ap.clicks) * 100.0) / SUM(ap.impressions), 3) AS ctr_pct,
                    ROUND(SUM(ap.ad_spend) / SUM(ap.clicks), 2) AS avg_cpc,
                    ROUND(SUM(ap.ad_spend) / SUM(ap.conversions), 2) AS avg_cpa,
                    ROUND((SUM(ap.conversions) * 100.0) / SUM(ap.clicks), 2) AS conversion_rate_pct,
                    ROUND(SUM(ap.client_conversion_revenue) / SUM(ap.ad_spend), 2) AS channel_roas
                FROM dim_campaigns cp
                JOIN fact_ad_performance ap ON cp.campaign_id = ap.campaign_id
                GROUP BY cp.marketing_channel
                ORDER BY total_ad_spend DESC;
            """
            
            # Query 3: Client Monthly Billing Cohorts
            sql_cohort = """
                WITH client_first_billing AS (
                    SELECT 
                        client_id,
                        MIN(invoice_date) AS first_billing_date,
                        strftime('%Y-%m', MIN(invoice_date)) AS cohort_month
                    FROM fact_client_billing
                    GROUP BY client_id
                ),
                
                cohort_sizes AS (
                    SELECT 
                        cohort_month,
                        COUNT(DISTINCT client_id) AS cohort_size,
                        SUM(total_billing_amount) AS initial_cohort_billing
                    FROM fact_client_billing
                    JOIN client_first_billing USING (client_id)
                    WHERE strftime('%Y-%m', invoice_date) = cohort_month
                    GROUP BY cohort_month
                ),
                
                monthly_billing_records AS (
                    SELECT 
                        c.cohort_month,
                        b.client_id,
                        b.total_billing_amount,
                        (
                            (CAST(strftime('%Y', b.invoice_date) AS INTEGER) - CAST(strftime('%Y', c.first_billing_date) AS INTEGER)) * 12
                        ) + (
                            CAST(strftime('%m', b.invoice_date) AS INTEGER) - CAST(strftime('%m', c.first_billing_date) AS INTEGER)
                        ) AS month_index
                    FROM fact_client_billing b
                    JOIN client_first_billing c ON b.client_id = c.client_id
                )
                
                SELECT 
                    r.cohort_month,
                    s.cohort_size,
                    r.month_index,
                    COUNT(DISTINCT r.client_id) AS active_clients,
                    ROUND(SUM(r.total_billing_amount), 2) AS total_billing,
                    ROUND((COUNT(DISTINCT r.client_id) * 100.0) / s.cohort_size, 2) AS client_retention_pct,
                    ROUND((SUM(r.total_billing_amount) * 100.0) / s.initial_cohort_billing, 2) AS revenue_retention_pct
                FROM monthly_billing_records r
                JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
                GROUP BY r.cohort_month, r.month_index
                ORDER BY r.cohort_month ASC, r.month_index ASC;
            """
            
            df_manager_res = pd.read_sql_query(sql_manager, conn)
            df_channel_res = pd.read_sql_query(sql_channel, conn)
            df_cohort_res = pd.read_sql_query(sql_cohort, conn)
            
            df_manager_res.to_csv(os.path.join(self.processed_dir, "manager_portfolio_results.csv"), index=False)
            df_channel_res.to_csv(os.path.join(self.processed_dir, "campaign_channel_results.csv"), index=False)
            df_cohort_res.to_csv(os.path.join(self.processed_dir, "client_billing_cohorts.csv"), index=False)
            
            logger.info("[SUCCESS] Advanced B2B SQL analytical CSV reports compiled and saved successfully!")
            logger.info("=== B2B AGENCY ETL PIPELINE COMPLETED SUCCESSFULLY ===")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error executing agency ETL: {e}")
            raise e
        finally:
            conn.close()

if __name__ == "__main__":
    pipeline = AgencyPipeline()
    pipeline.run_etl()
