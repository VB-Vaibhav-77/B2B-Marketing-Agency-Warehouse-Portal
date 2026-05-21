import os
import sqlite3
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("DB_Loader")

class DatabaseLoader:
    def __init__(self, db_path="data/apex_analytics.db", processed_dir="data/processed", sql_schema_path="src/sql/schema_ddl.sql"):
        self.db_path = db_path
        self.processed_dir = processed_dir
        self.sql_schema_path = sql_schema_path
        
        # Ensure data folder exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def load_database(self):
        logger.info("Connecting to SQLite database...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. INITIALIZE SCHEMA DDL
            logger.info(f"Executing schema DDL script from {self.sql_schema_path}...")
            with open(self.sql_schema_path, "r", encoding="utf-8") as f:
                ddl_script = f.read()
                
            # Execute multiple SQL statements separated by semicolon
            cursor.executescript(ddl_script)
            conn.commit()
            logger.info("Database schema initialized successfully.")
            
            # 2. LOAD DATA FROM CSVs
            tables_to_load = {
                "dim_customers": "dim_customers.csv",
                "dim_products": "dim_products.csv",
                "dim_date": "dim_date.csv",
                "fact_sales": "fact_sales.csv",
                "fact_web_traffic": "fact_web_traffic.csv"
            }
            
            for table_name, csv_filename in tables_to_load.items():
                csv_path = os.path.join(self.processed_dir, csv_filename)
                if not os.path.exists(csv_path):
                    raise FileNotFoundError(f"Missing processed data file: {csv_path}")
                    
                logger.info(f"Reading processed CSV for {table_name}...")
                df = pd.read_csv(csv_path)
                
                logger.info(f"Loading {df.shape[0]} rows into database table '{table_name}'...")
                # Write to SQLite
                df.to_sql(table_name, conn, if_exists="append", index=False)
                conn.commit()
                
                # Verify row counts
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                loaded_count = cursor.fetchone()[0]
                logger.info(f" -> Verification: Loaded {loaded_count} rows into '{table_name}'.")
                
            logger.info("All tables successfully loaded into the SQLite relational database!")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error occurred during database loading: {e}")
            raise e
        finally:
            conn.close()

if __name__ == "__main__":
    loader = DatabaseLoader()
    loader.load_database()
