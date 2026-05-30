import sys
import logging
from src.data_generator.generate_raw_data import generate_data
from src.etl.etl_pipeline import EcomETL
from src.etl.db_loader import DatabaseLoader
from src.etl.data_validation import DataValidator
from src.etl.sql_executor import AnalyticsSQLExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DataPipeline")

def main():
    logger.info("Starting B2C E-Commerce Data Pipeline")
    
    try:
        # Step 1: Generate raw synthetic data
        logger.info("Step 1: Generating raw transactional data")
        generate_data()
        
        # Step 2: Clean and model star schema (ETL)
        logger.info("Step 2: Running ETL transformations")
        pipeline = EcomETL()
        pipeline.run_pipeline()
        
        # Step 3: Load cleaned data into local SQLite database
        logger.info("Step 3: Loading relational schema into database")
        loader = DatabaseLoader()
        loader.load_database()
        
        # Step 4: Run data quality validations
        logger.info("Step 4: Running data quality test suite")
        validator = DataValidator()
        validation_success = validator.run_validations()
        
        # Step 5: Run analytical queries
        logger.info("Step 5: Compiling SQL analytical models (RFM & Cohorts)")
        executor = AnalyticsSQLExecutor()
        executor.execute_and_export()
        
        if validation_success:
            logger.info("Data pipeline completed successfully. SQLite DB compiled at: data/apex_analytics.db")
        else:
            logger.warning("Pipeline completed with data validation errors. Review: data/data_validation_report.csv")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
