import sys
import logging
from src.data_generator.generate_agency_data import generate_agency_data
from src.etl.agency_etl import AgencyPipeline
from src.etl.data_validation import AgencyDataValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AgencyPipeline")

def main():
    logger.info("Starting B2B Marketing Agency Data Pipeline")
    
    try:
        # Step 1: Generate raw B2B agency data
        logger.info("Step 1: Generating raw B2B agency data")
        generate_agency_data()
        
        # Step 2: Clean and model Galaxy schema (ETL & Analytical Views)
        logger.info("Step 2: Running ETL and B2B analytical query compiles")
        pipeline = AgencyPipeline()
        pipeline.run_etl()
        
        # Step 3: Run database quality validation tests
        logger.info("Step 3: Executing B2B validation suite")
        validator = AgencyDataValidator()
        validation_success = validator.run_validations()
        
        if validation_success:
            logger.info("B2B pipeline executed successfully. SQLite DB compiled at: data/agency_analytics.db")
        else:
            logger.warning("Pipeline completed with validation warnings. Review: data/agency_validation_report.csv")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
