import os
import sys
import pandas as pd
import pydata_google_auth

def main():
    print("Starting B2B BigQuery Uploader Script")
    
    processed_dir = os.path.join("data", "processed_agency")
    if not os.path.exists(processed_dir):
        print(f"Error: Processed directory not found at '{processed_dir}'")
        print("Please run 'python main_agency.py' to generate B2B datasets first.")
        sys.exit(1)

    tables_to_upload = {
        "dim_account_managers": "dim_account_managers.csv",
        "dim_clients": "dim_clients.csv",
        "dim_campaigns": "dim_campaigns.csv",
        "dim_date_agency": "dim_date.csv",
        "fact_ad_performance": "fact_ad_performance.csv",
        "fact_client_billing": "fact_client_billing.csv",
        "manager_portfolio_results": "manager_portfolio_results.csv",
        "campaign_channel_results": "campaign_channel_results.csv",
        "client_billing_cohorts": "client_billing_cohorts.csv"
    }

    # Verify all CSVs exist before starting upload
    for table_name, csv_filename in tables_to_upload.items():
        csv_path = os.path.join(processed_dir, csv_filename)
        if not os.path.exists(csv_path):
            print(f"Error: Missing required B2B CSV file: '{csv_path}'")
            print("Please run 'python main_agency.py' to compile B2B assets first.")
            sys.exit(1)

    project_id = os.environ.get("GCP_PROJECT_ID", "").strip()
    if project_id:
        print(f"GCP Project ID loaded from environment: {project_id}")
    else:
        project_id = input("Enter GCP Project ID: ").strip()
        if not project_id:
            print("Error: GCP Project ID is required.")
            sys.exit(1)

    import json
    print("\nAuthenticating with Google Cloud Platform...")
    
    try:
        credentials = None
        gcp_key_env = os.environ.get("GCP_CREDENTIALS")
        
        if gcp_key_env:
            # 1. Load from environment variable (CI/CD cloud pipeline)
            print("Loading credentials from environment variable...")
            import google.oauth2.service_account
            key_dict = json.loads(gcp_key_env)
            credentials = google.oauth2.service_account.Credentials.from_service_account_info(
                key_dict,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        elif os.path.exists(os.path.join("data", "gcp_credentials.json")):
            # 2. Load from local JSON key file
            print("Loading credentials from local data/gcp_credentials.json...")
            import google.oauth2.service_account
            credentials = google.oauth2.service_account.Credentials.from_service_account_file(
                os.path.join("data", "gcp_credentials.json"),
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        else:
            # 3. Fallback to interactive OAuth
            print("Triggering Google OAuth browser authentication...")
            credentials = pydata_google_auth.get_user_credentials(
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
                auth_local_webserver=True
            )
        
        print("Authentication successful.")
        print(f"Target Project: {project_id}")
        print(f"Target Dataset: apex_analytics\n")
        
        # Ensure target dataset exists
        from google.cloud import bigquery
        client = bigquery.Client(project=project_id, credentials=credentials)
        dataset_id = f"{project_id}.apex_analytics"
        
        print(f"Checking dataset 'apex_analytics'...")
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        
        try:
            client.get_dataset(dataset_id)
            print("Dataset 'apex_analytics' exists.")
        except Exception:
            print("Dataset 'apex_analytics' not found. Creating dataset...")
            client.create_dataset(dataset, timeout=30)
            print("Dataset created successfully.")

        # Upload tables
        print("\nUploading B2B tables to BigQuery:")
        for table_name, csv_filename in tables_to_upload.items():
            csv_path = os.path.join(processed_dir, csv_filename)
            destination_table = f"apex_analytics.{table_name}"
            
            print(f"Uploading '{csv_filename}' to '{destination_table}'...")
            df = pd.read_csv(csv_path)
            
            import pandas_gbq
            pandas_gbq.to_gbq(
                df,
                destination_table=destination_table,
                project_id=project_id,
                credentials=credentials,
                if_exists="replace",
                progress_bar=False
            )
            print(f"Successfully uploaded {len(df)} rows.")

        print("\nB2B tables upload completed successfully.")

    except Exception as e:
        print(f"\nError occurred during BigQuery process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
