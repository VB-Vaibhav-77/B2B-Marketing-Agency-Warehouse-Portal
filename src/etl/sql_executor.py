import os
import sqlite3
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("SQL_Executor")

class AnalyticsSQLExecutor:
    def __init__(self, db_path="data/apex_analytics.db", sql_dir="src/sql", output_dir="data/processed"):
        self.db_path = db_path
        self.sql_dir = sql_dir
        self.output_dir = output_dir
        
        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)

    def execute_and_export(self):
        logger.info("Connecting to SQLite database for analytical executions...")
        conn = sqlite3.connect(self.db_path)
        
        queries_to_run = {
            "cohort_retention": "cohort_retention.sql",
            "rfm_segmentation": "rfm_segmentation.sql",
            "attribution_analysis": "attribution_analysis.sql"
        }
        
        try:
            for key, sql_filename in queries_to_run.items():
                sql_path = os.path.join(self.sql_dir, sql_filename)
                if not os.path.exists(sql_path):
                    raise FileNotFoundError(f"Missing analytical SQL script: {sql_path}")
                
                logger.info(f"Reading SQL script: {sql_filename}...")
                with open(sql_path, "r", encoding="utf-8") as f:
                    query = f.read()
                
                logger.info(f"Executing query and loading into DataFrame for {key}...")
                # SQLite executes the clean SQL code directly
                df = pd.read_sql_query(query, conn)
                
                # Define output path
                output_filename = f"{key}_results.csv"
                output_path = os.path.join(self.output_dir, output_filename)
                
                logger.info(f"Saving {df.shape[0]} results rows to CSV at: {output_path}...")
                df.to_csv(output_path, index=False)
                
            logger.info("🎉 All advanced SQL analytical queries executed and exported successfully!")
            
        except Exception as e:
            logger.error(f"Error executing and exporting analytics: {e}")
            raise e
        finally:
            conn.close()

if __name__ == "__main__":
    executor = AnalyticsSQLExecutor()
    executor.execute_and_export()
