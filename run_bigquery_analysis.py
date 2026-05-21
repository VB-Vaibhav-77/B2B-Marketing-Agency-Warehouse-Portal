import os
import sys
import pandas as pd
import pydata_google_auth

def main():
    print("=" * 70)
    print("   🚀 ApexAnalytics - Google BigQuery Cloud Execution Runner 🚀   ")
    print("=" * 70)
    print("This automation script will run your Marketing Attribution Analysis")
    print("directly inside your Google BigQuery Cloud Sandbox from PowerShell.")
    print("Zero copy-paste syntax errors guaranteed!\n")

    # Step 1: Locate and read the SQL query file
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

    # Step 2: Get Google Cloud Project ID from the user
    print("💡 Tip: You can find your Project ID at the top left of the Google Cloud console.")
    project_id = input("👉 Enter your Google Cloud Project ID: ").strip()
    if not project_id:
        print("❌ Error: Project ID cannot be empty. Please run the script again.")
        sys.exit(1)

    print(f"\n🔐 Triggering Google OAuth authentication...")
    print("A browser window will open shortly. Please select your Google account and click 'Allow'.\n")

    try:
        # Request standard BigQuery cloud-platform scopes
        credentials = pydata_google_auth.get_user_credentials(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
            auth_local_webserver=True
        )
        
        print("✓ Credentials successfully authenticated!")
        print(f"✓ Preparing query on project: {project_id}")
        
        # Format the query by replacing relative dataset paths with absolute PROJECT_ID paths
        # This prevents any "Dataset not found" or routing errors.
        formatted_query = query.replace("`apex_analytics.", f"`{project_id}.apex_analytics.")
        
        print("\n⏳ Executing query in Google Cloud BigQuery... please wait a few seconds...")
        
        # Execute query using pandas-gbq
        df = pd.read_gbq(
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
        
        # Step 5: Save results locally to a CSV file
        output_csv = os.path.join("data", "bigquery_attribution_results.csv")
        os.makedirs("data", exist_ok=True)
        df.to_csv(output_csv, index=False)
        print(f"\n🎉 Success! Cloud query executed successfully!")
        print(f"📂 Results saved locally to your workspace at: {output_csv}")
        
        # Step 6: Create permanent view inside BigQuery console
        print(f"\n🛠️ Creating a permanent view 'view_marketing_attribution' inside your BigQuery 'apex_analytics' dataset...")
        from google.cloud import bigquery
        client = bigquery.Client(project=project_id, credentials=credentials)
        view_ddl = f"CREATE OR REPLACE VIEW `{project_id}.apex_analytics.view_marketing_attribution` AS\n{formatted_query}"
        client.query(view_ddl).result()
        print("✅ Success! View 'view_marketing_attribution' is now created permanently in your BigQuery account.")
        print("👉 Just open or refresh your BigQuery Console (https://console.cloud.google.com/bigquery) and you will see it listed under your 'apex_analytics' dataset!")

        
    except Exception as e:
        print(f"\n❌ Error executing query: {e}")
        print("\n💡 Troubleshooting Tips:")
        print("1. Verify your Google Cloud Project ID is spelled exactly right.")
        print("2. Ensure all 5 tables are successfully loaded inside your dataset named 'apex_analytics'.")
        print("3. Make sure you are logging in with the Google Account that owns the Google Cloud Sandbox project.")
        print("4. Verify that you checked 'Auto detect' schema when uploading the tables in BigQuery.")
        sys.exit(1)

if __name__ == "__main__":
    main()
