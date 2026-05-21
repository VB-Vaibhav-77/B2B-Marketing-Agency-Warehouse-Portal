import sys
import logging
from src.data_generator.generate_raw_data import generate_data
from src.etl.etl_pipeline import EcomETL
from src.etl.db_loader import DatabaseLoader
from src.etl.data_validation import DataValidator
from src.etl.sql_executor import AnalyticsSQLExecutor

# Configure beautiful logging formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ApexAnalytics_Main")

def main():
    logger.info("================================================================")
    logger.info("     APEXANALYTICS: END-TO-END DATA ENGINEERING PIPELINE")
    logger.info("================================================================")
    
    try:
        # Step 1: Generate Synthetic Raw Data
        logger.info("\n--- STEP 1: GENERATING HIGH-FIDELITY RAW DATA ---")
        generate_data()
        
        # Step 2: Clean & Model Star Schema (ETL)
        logger.info("\n--- STEP 2: RUNNING ETL PIPELINE (CLEAN & STAR SCHEMA) ---")
        pipeline = EcomETL()
        pipeline.run_pipeline()
        
        # Step 3: Load Data into SQLite Database
        logger.info("\n--- STEP 3: LOADING DATA INTO RELATIONAL SQL DATABASE ---")
        loader = DatabaseLoader()
        loader.load_database()
        
        # Step 4: Run Data Quality Validations
        logger.info("\n--- STEP 4: RUNNING DATA QUALITY VALIDATION SUITE ---")
        validator = DataValidator()
        validation_success = validator.run_validations()
        
        # Step 5: Execute Advanced Analytical Queries
        logger.info("\n--- STEP 5: COMPILING ADVANCED SQL ANALYTICS (RFM & COHORTS) ---")
        executor = AnalyticsSQLExecutor()
        executor.execute_and_export()
        
        logger.info("\n================================================================")
        if validation_success:
            logger.info("🎉 PIPELINE EXECUTION SUCCESSFUL: All tables cleaned, loaded, & analyzed!")
            logger.info("Your SQLite database is compiled at: data/apex_analytics.db")
            logger.info("Clean star schema & analytical CSVs are exported at: data/processed/")
        else:
            logger.warning("⚠️ PIPELINE COMPLETED WITH DATA VALIDATION ERRORS.")
            logger.warning("Review report details at: data/data_validation_report.csv")
        logger.info("================================================================")
        
    except Exception as e:
        logger.error(f"\n❌ PIPELINE CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
