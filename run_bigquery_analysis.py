import os
import sys
import pandas as pd
import pydata_google_auth

def main():
    print("Starting B2C BigQuery Uploader & Analytics Script")
    
    processed_dir = os.path.join("data", "processed")
    if not os.path.exists(processed_dir):
        print(f"Error: Processed directory not found at '{processed_dir}'")
        print("Please run 'python main.py' to generate B2C datasets first.")
        sys.exit(1)

    tables_to_upload = {
        "dim_customers": "dim_customers.csv",
        "dim_products": "dim_products.csv",
        "dim_date": "dim_date.csv",
        "fact_sales": "fact_sales.csv",
        "fact_web_traffic": "fact_web_traffic.csv",
        "rfm_segmentation_results": "rfm_segmentation_results.csv",
        "cohort_retention_results": "cohort_retention_results.csv"
    }

    # Verify all CSVs exist before starting upload
    for table_name, csv_filename in tables_to_upload.items():
        csv_path = os.path.join(processed_dir, csv_filename)
        if not os.path.exists(csv_path):
            print(f"Error: Missing required B2C CSV file: '{csv_path}'")
            print("Please run 'python main.py' to compile analytical outputs first.")
            sys.exit(1)

    sql_path = os.path.join("src", "sql", "bigquery_attribution.sql")
    if not os.path.exists(sql_path):
        print(f"Error: Missing SQL query file: '{sql_path}'")
        sys.exit(1)
        
    try:
        with open(sql_path, "r", encoding="utf-8") as f:
            query = f.read()
    except Exception as e:
        print(f"Error reading SQL file: {e}")
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
        print("\nUploading B2C tables to BigQuery:")
        for table_name, csv_filename in tables_to_upload.items():
            csv_path = os.path.join(processed_dir, csv_filename)
            destination_table = f"apex_analytics.{table_name}"
            
            print(f"Uploading '{csv_filename}' to '{destination_table}'...")
            df_table = pd.read_csv(csv_path)
            
            import pandas_gbq
            pandas_gbq.to_gbq(
                df_table,
                destination_table=destination_table,
                project_id=project_id,
                credentials=credentials,
                if_exists="replace",
                progress_bar=False
            )
            print(f"Successfully uploaded {len(df_table)} rows.")

        # Format and execute marketing attribution query
        formatted_query = query.replace("`apex_analytics.", f"`{project_id}.apex_analytics.")
        print("\nRunning Attribution analytical query in BigQuery...")
        
        import pandas_gbq
        df = pandas_gbq.read_gbq(
            formatted_query,
            project_id=project_id,
            credentials=credentials,
            dialect="standard"
        )
        
        print("\nBigQuery Marketing Attribution Results:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.colheader_justify', 'center')
        print(df.to_string(index=False))
        
        output_csv = os.path.join("data", "bigquery_attribution_results.csv")
        df.to_csv(output_csv, index=False)
        print(f"\nAttribution query completed. Local results saved to: {output_csv}")
        
        # Save permanent view in BigQuery
        print("\nCreating view 'view_marketing_attribution' in BigQuery...")
        view_ddl = f"CREATE OR REPLACE VIEW `{project_id}.apex_analytics.view_marketing_attribution` AS\n{formatted_query}"
        client.query(view_ddl).result()
        print("View created successfully.")

    except Exception as e:
        print(f"\nError occurred during BigQuery process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
