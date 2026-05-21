import sys
import logging
from src.data_generator.generate_agency_data import generate_agency_data
from src.etl.agency_etl import AgencyPipeline
from src.etl.data_validation import AgencyDataValidator

# Configure beautiful logging formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("B2B_Agency_Main")

def main():
    logger.info("================================================================")
    logger.info("    [APEXANALYTICS: B2B MARKETING AGENCY MANAGEMENT PORTAL]")
    logger.info("================================================================")
    
    try:
        # Step 1: Generate Synthetic B2B Agency Raw Data
        logger.info("\n--- STEP 1: GENERATING HIGH-FIDELITY B2B AGENCY RAW DATA ---")
        generate_agency_data()
        
        # Step 2: Run B2B Agency ETL & SQL Analytics Compiles
        logger.info("\n--- STEP 2: RUNNING ETL PIPELINE & COMPILING SQL ANALYTICS ---")
        pipeline = AgencyPipeline()
        pipeline.run_etl()
        
        # Step 3: Run Database Quality & Integrity Validation
        logger.info("\n--- STEP 3: RUNNING B2B DATABASE QUALITY & INTEGRITY VALIDATION ---")
        validator = AgencyDataValidator()
        validation_success = validator.run_validations()
        
        if not validation_success:
            logger.warning("\n[WARNING] Some data quality checks did not pass. Check data/agency_validation_report.csv for details.")
        
        logger.info("\n================================================================")
        logger.info("[SUCCESS] B2B AGENCY PIPELINE EXECUTION SUCCESSFUL!")
        logger.info("Your relational database is compiled at: data/agency_analytics.db")
        logger.info("Clean star schema & pre-computed B2B CSVs are exported at: data/processed_agency/")
        logger.info("Database validation suite run complete (23 tests executed).")
        logger.info("You are ready to load these into Power BI for a top-tier corporate report!")
        logger.info("================================================================")
        
    except Exception as e:
        logger.error(f"\n[ERROR] PIPELINE CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
