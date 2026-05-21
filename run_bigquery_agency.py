import os
import sys
import pandas as pd
import pydata_google_auth

def main():
    print("=" * 75)
    print("   🚀 APEXANALYTICS: B2B MARKETING AGENCY - BIGQUERY CLOUD UPLOADER 🚀   ")
    print("=" * 75)
    print("This automated script will upload all 9 clean B2B Marketing Agency tables")
    print("directly into your Google BigQuery Cloud Sandbox from your terminal.")
    print("No service account keys or JSON configuration required!\n")

    # Step 1: Verify the processed CSV files exist locally
    processed_dir = os.path.join("data", "processed_agency")
    if not os.path.exists(processed_dir):
        print(f"❌ Error: Could not find B2B agency CSV directory at '{processed_dir}'")
        print("💡 Tip: Please run 'python main_agency.py' first to compile the clean B2B data!")
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

    # Verify all CSVs exist before initiating login
    for table_name, csv_filename in tables_to_upload.items():
        csv_path = os.path.join(processed_dir, csv_filename)
        if not os.path.exists(csv_path):
            print(f"❌ Error: Missing required B2B CSV file: '{csv_path}'")
            print("💡 Please execute 'python main_agency.py' to generate all pre-computed assets.")
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

        # Step 4: Load and Upload each B2B table using pandas-gbq
        print("\n" + "═" * 70)
        print("                UPLOADING B2B DATASETS TO GOOGLE BIGQUERY")
        print("═" * 70)

        for table_name, csv_filename in tables_to_upload.items():
            csv_path = os.path.join(processed_dir, csv_filename)
            destination_table = f"apex_analytics.{table_name}"
            
            print(f"⏳ Uploading '{csv_filename}' to table '{destination_table}'...")
            
            # Read CSV local data
            df = pd.read_csv(csv_path)
            
            # Upload using pandas-gbq
            df.to_gbq(
                destination_table=destination_table,
                project_id=project_id,
                credentials=credentials,
                if_exists="replace",  # Overwrites/replaces with fresh data
                progress_bar=True
            )
            
            print(f"✅ Success! Loaded {len(df)} rows into table '{table_name}'.\n")

        print("═" * 70)
        print("\n🎉 CONGRATULATIONS! ALL 9 B2B AGENCY TABLES ARE LOADED IN BIGQUERY!")
        print("👉 Open your Google BigQuery Console (https://console.cloud.google.com/bigquery)")
        print("   Refresh the 'apex_analytics' dataset, and you will see your new B2B tables")
        print("   listed beautifully alongside the existing B2C tables!")
        print("=" * 75)

    except Exception as e:
        print(f"\n❌ Error during Cloud Upload: {e}")
        print("\n💡 Troubleshooting Tips:")
        print("1. Double check that your Google Cloud Project ID is spelled exactly right.")
        print("2. Make sure you are logging in with the Google Account that owns the Google Cloud Sandbox project.")
        print("3. Ensure that you have the required python dependencies installed by running:")
        print("   pip install pandas-gbq pydata-google-auth google-cloud-bigquery")
        sys.exit(1)

if __name__ == "__main__":
    main()
