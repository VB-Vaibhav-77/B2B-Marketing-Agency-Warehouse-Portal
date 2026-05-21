import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("BigQuery_Loader")

def print_gcp_instructions():
    logger.error("==========================================================================")
    logger.error("❌ GOOGLE GCP SERVICE ACCOUNT KEY NOT FOUND!")
    logger.error("==========================================================================")
    logger.error("Since Google BigQuery is secured by your personal Google account, you must")
    logger.error("provide a secure access key so this Python script can load data for you.")
    logger.error("\nFollow these 5 simple steps in your web browser to get your key:")
    logger.error("1. Open: https://console.cloud.google.com/iam-admin/serviceaccounts")
    logger.error("2. Select your GCP project at the top (or create one in 5 seconds).")
    logger.error("3. Click '+ CREATE SERVICE ACCOUNT' at the top, name it 'apex-pipeline',")
    logger.error("   grant it the role 'BigQuery Admin', and click 'Done'.")
    logger.error("4. Click on your newly created service account in the list, go to the 'KEYS' tab,")
    logger.error("   click 'ADD KEY' -> 'Create new key', select 'JSON' format, and click 'Create'.")
    logger.error("5. A file will download to your PC. Move or rename that file to:")
    logger.error("   C:\\Users\\vaibh\\Documents\\antigravity\\fervent-salk\\data\\gcp_credentials.json")
    logger.error("==========================================================================")
    logger.error("Once the key is saved at that location, run this script again!")

def upload_to_bigquery():
    credentials_path = "data/gcp_credentials.json"
    
    if not os.path.exists(credentials_path):
        print_gcp_instructions()
        sys.exit(1)
        
    try:
        # Import BigQuery client libraries inside the function to avoid errors if not installed yet
        from google.cloud import bigquery
        from google.oauth2 import service_account
    except ImportError:
        logger.info("Installing required Google Cloud BigQuery Python libraries...")
        # Proactively install libraries using pip
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "google-cloud-bigquery", "pandas-gbq"])
        from google.cloud import bigquery
        from google.oauth2 import service_account

    logger.info("Connecting to Google Cloud BigQuery using service account credentials...")
    
    try:
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        project_id = credentials.project_id
        
        # Initialize client
        client = bigquery.Client(credentials=credentials, project=project_id)
        
        dataset_id = f"{project_id}.apex_analytics"
        
        # 1. Create dataset if not exists
        logger.info(f"Checking for dataset '{dataset_id}' in Google Cloud...")
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"  # Standard US multi-region
        
        try:
            client.get_dataset(dataset_id)
            logger.info(" -> Dataset already exists.")
        except Exception:
            logger.info(f" -> Creating new dataset '{dataset_id}'...")
            client.create_dataset(dataset, timeout=30)
            logger.info(" -> Dataset created successfully.")
            
        # 2. Upload CSVs
        processed_dir = "data/processed"
        tables_to_load = {
            "dim_customers": "dim_customers.csv",
            "dim_products": "dim_products.csv",
            "dim_date": "dim_date.csv",
            "fact_sales": "fact_sales.csv"
        }
        
        for table_name, csv_filename in tables_to_load.items():
            csv_path = os.path.join(processed_dir, csv_filename)
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"Missing processed CSV file: {csv_path}")
                
            table_ref = f"{dataset_id}.{table_name}"
            logger.info(f"Uploading {csv_filename} to BigQuery table '{table_ref}'...")
            
            # Configure upload job settings
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.CSV,
                skip_leading_rows=1,
                autodetect=True,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE  # Overwrites existing data
            )
            
            with open(csv_path, "rb") as source_file:
                load_job = client.load_table_from_file(
                    source_file,
                    table_ref,
                    job_config=job_config
                )
                
            load_job.result()  # Wait for upload job to complete
            
            # Verify row counts
            table = client.get_table(table_ref)
            logger.info(f" -> Success! Loaded {table.num_rows} rows into BigQuery table '{table_name}'.")
            
        logger.info("\n==========================================================================")
        logger.info("🎉 CLOUD DEPLOYMENT COMPLETED! All tables are loaded in Google BigQuery.")
        logger.info("You can now open the BigQuery browser console and run standard SQL queries!")
        logger.info("==========================================================================")
        
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR during BigQuery upload: {e}")
        sys.exit(1)

if __name__ == "__main__":
    upload_to_bigquery()
