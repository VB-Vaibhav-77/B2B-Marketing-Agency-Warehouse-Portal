import os
import sys
import pandas as pd
import pydata_google_auth

def main():
    print("=" * 80)
    print("   🚀 APEXANALYTICS: B2C E-COMMERCE - BIGQUERY CLOUD UPLOADER & ANALYZER 🚀   ")
    print("=" * 80)
    print("This automated script will upload all 5 clean B2C E-Commerce tables")
    print("directly into your Google BigQuery Cloud Sandbox from your terminal,")
    print("and then execute advanced marketing attribution analytics.\n")

    # Step 1: Verify the processed CSV files exist locally
    processed_dir = os.path.join("data", "processed")
    if not os.path.exists(processed_dir):
        print(f"❌ Error: Could not find B2C processed CSV directory at '{processed_dir}'")
        print("💡 Tip: Please run 'python main.py' first to compile the clean B2C data!")
        sys.exit(1)

    tables_to_upload = {
        "dim_customers": "dim_customers.csv",
        "dim_products": "dim_products.csv",
        "dim_date": "dim_date.csv",
        "fact_sales": "fact_sales.csv",
        "fact_web_traffic": "fact_web_traffic.csv"
    }

    # Verify all CSVs exist before initiating login
    for table_name, csv_filename in tables_to_upload.items():
        csv_path = os.path.join(processed_dir, csv_filename)
        if not os.path.exists(csv_path):
            print(f"❌ Error: Missing required B2C CSV file: '{csv_path}'")
            print("💡 Please execute 'python main.py' to generate all pre-computed B2C assets.")
            sys.exit(1)

    # Locate and read the SQL query file
    sql_path = os.path.join("src", "sql", "bigquery_attribution.sql")
    if not os.path.exists(sql_path):
        print(f"❌ Error: Could not find SQL file at '{sql_path}'")
        sys.exit(1)
        
    try:
        with open(sql_path, "r", encoding="utf-8") as f:
            query = f.read()
    except Exception as e:
        print(f"❌ Error reading SQL file: {e}")
        sys.exit(1)

    # Step 2: Get Google Cloud Project ID
    project_id = os.environ.get("GCP_PROJECT_ID", "").strip()
    if project_id:
        print(f"👉 Using Project ID from environment: {project_id}")
    else:
        print("💡 Tip: Find your Project ID at the top left of your Google Cloud Console (https://console.cloud.google.com/).")
        project_id = input("👉 Enter your Google Cloud Project ID: ").strip()
        if not project_id:
            print("❌ Error: Project ID cannot be empty. Please run the script again.")
            sys.exit(1)

    import json
    print("\n🔐 Authenticating with Google Cloud Platform...")

    try:
        credentials = None
        gcp_key_env = os.environ.get("GCP_CREDENTIALS")
        
        if gcp_key_env:
            # 1. Load from environment variable (CI/CD cloud uploader)
            print(" -> [CLOUD] Loading credentials from GitHub Action Secret environment variable...")
            import google.oauth2.service_account
            key_dict = json.loads(gcp_key_env)
            credentials = google.oauth2.service_account.Credentials.from_service_account_info(
                key_dict,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        elif os.path.exists(os.path.join("data", "gcp_credentials.json")):
            # 2. Load from local git-ignored JSON key
            print(" -> [KEYFILE] Loading credentials from local git-ignored JSON key...")
            import google.oauth2.service_account
            credentials = google.oauth2.service_account.Credentials.from_service_account_file(
                os.path.join("data", "gcp_credentials.json"),
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        else:
            # 3. Fallback to interactive browser OAuth (Default local behavior)
            print(" -> [OAuth] Triggering Google OAuth interactive browser login...")
            print("A browser window will open shortly. Please select your Google account and click 'Allow'.\n")
            credentials = pydata_google_auth.get_user_credentials(
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
                auth_local_webserver=True
            )
        
        print("✓ Credentials successfully authenticated!")
        print(f"✓ Target Project: {project_id}")
        print(f"✓ Target Dataset: apex_analytics\n")

        # Step 3: Initialize BigQuery Client to ensure dataset exists
        from google.cloud import bigquery
        client = bigquery.Client(project=project_id, credentials=credentials)
        dataset_id = f"{project_id}.apex_analytics"
        
        print(f"⏳ Verification: Ensuring BigQuery dataset 'apex_analytics' exists...")
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        
        try:
            client.get_dataset(dataset_id)
            print(" -> [OK] Dataset 'apex_analytics' exists.")
        except Exception:
            print(" -> [CREATE] Dataset 'apex_analytics' not found. Initializing now...")
            client.create_dataset(dataset, timeout=30)
            print(" -> [OK] Dataset 'apex_analytics' created successfully.")

        # Step 4: Load and Upload each B2C table using pandas-gbq
        print("\n" + "═" * 70)
        print("                UPLOADING B2C DATASETS TO GOOGLE BIGQUERY")
        print("═" * 70)

        for table_name, csv_filename in tables_to_upload.items():
            csv_path = os.path.join(processed_dir, csv_filename)
            destination_table = f"apex_analytics.{table_name}"
            
            print(f"⏳ Uploading '{csv_filename}' to table '{destination_table}'...")
            
            # Read CSV local data
            df_table = pd.read_csv(csv_path)
            
            # Upload using pandas-gbq
            import pandas_gbq
            pandas_gbq.to_gbq(
                df_table,
                destination_table=destination_table,
                project_id=project_id,
                credentials=credentials,
                if_exists="replace",  # Overwrites/replaces with fresh data
                progress_bar=True
            )
            
            print(f"✅ Success! Loaded {len(df_table)} rows into table '{table_name}'.\n")

        print("═" * 70)
        
        # Step 5: Format and Execute SQL analytics query
        # Format the query by replacing relative dataset paths with absolute PROJECT_ID paths
        formatted_query = query.replace("`apex_analytics.", f"`{project_id}.apex_analytics.")
        
        print("\n⏳ Executing Attribution query in Google Cloud BigQuery... please wait a few seconds...")
        
        # Execute query using pandas-gbq
        import pandas_gbq
        df = pandas_gbq.read_gbq(
            formatted_query,
            project_id=project_id,
            credentials=credentials,
            dialect="standard"
        )
        
        # Display the results beautifully in the terminal
        print("\n" + "═" * 115)
        print("                                       BIGQUERY MARKETING ATTRIBUTION RESULTS")
        print("═" * 115)
        
        # Configure Pandas layout to show all columns clearly
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.colheader_justify', 'center')
        
        print(df.to_string(index=False))
        print("═" * 115)
        
        # Step 6: Save results locally to a CSV file
        output_csv = os.path.join("data", "bigquery_attribution_results.csv")
        df.to_csv(output_csv, index=False)
        print(f"\n🎉 Success! Cloud query executed successfully!")
        print(f"📂 Results saved locally to your workspace at: {output_csv}")
        
        # Step 7: Create permanent view inside BigQuery console
        print(f"\n🛠️ Creating a permanent view 'view_marketing_attribution' inside your BigQuery 'apex_analytics' dataset...")
        view_ddl = f"CREATE OR REPLACE VIEW `{project_id}.apex_analytics.view_marketing_attribution` AS\n{formatted_query}"
        client.query(view_ddl).result()
        print("✅ Success! View 'view_marketing_attribution' is now created permanently in your BigQuery account.")
        print("👉 Open or refresh your BigQuery Console (https://console.cloud.google.com/bigquery) to see it listed under your 'apex_analytics' dataset!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during Cloud execution: {e}")
        print("\n💡 Troubleshooting Tips:")
        print("1. Double check that your Google Cloud Project ID is spelled exactly right.")
        print("2. Make sure you are logging in with the Google Account that owns the Google Cloud Sandbox project.")
        print("3. Ensure that you have the required python dependencies installed by running:")
        print("   pip install pandas-gbq pydata-google-auth google-cloud-bigquery")
        sys.exit(1)

if __name__ == "__main__":
    main()
