import os
import sys
import json
import base64
import subprocess
import pydata_google_auth
import google.auth.transport.requests

def main():
    print("Starting Automated Google GCP Service Account & GitHub Secrets Configurator")
    
    project_id = os.environ.get("GCP_PROJECT_ID", "").strip()
    if not project_id:
        project_id = input("Enter Google Cloud Project ID: ").strip()
    if not project_id:
        print("Error: GCP Project ID is required.")
        sys.exit(1)
        
    print("\nAuthenticating with Google Cloud Platform...")
    try:
        credentials = pydata_google_auth.get_user_credentials(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
            auth_local_webserver=True
        )
        # Refresh credential to retrieve access token
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        token = credentials.token
    except Exception as e:
        print(f"Auth Error: {e}")
        sys.exit(1)
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id
    }
    
    sa_name = "github-actions-bq"
    sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"
    
    # Create service account
    print(f"\nCreating Service Account '{sa_name}' in project '{project_id}'...")
    create_url = f"https://iam.googleapis.com/v1/projects/{project_id}/serviceAccounts"
    create_data = {
        "accountId": sa_name,
        "serviceAccount": {
            "displayName": "GitHub Actions BigQuery CI/CD Uploader"
        }
    }
    
    import requests
    resp = requests.post(create_url, headers=headers, json=create_data)
    if resp.status_code == 200:
        print("Service Account created successfully.")
    elif resp.status_code == 409:
        print("Service Account already exists.")
    else:
        print(f"Error creating Service Account: {resp.text}")
        sys.exit(1)
        
    # Grant BigQuery Admin role
    print("\nGranting BigQuery Admin role to the Service Account...")
    policy_url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:getIamPolicy"
    policy_resp = requests.post(policy_url, headers=headers)
    if policy_resp.status_code != 200:
        print(f"Error getting IAM policy: {policy_resp.text}")
        print("Note: Ensure your authenticated account has Owner or Editor permissions on the project.")
        sys.exit(1)
        
    policy = policy_resp.json()
    role_to_add = "roles/bigquery.admin"
    member = f"serviceAccount:{sa_email}"
    
    found_binding = False
    for binding in policy.get("bindings", []):
        if binding["role"] == role_to_add:
            if member not in binding["members"]:
                binding["members"].append(member)
            found_binding = True
            break
            
    if not found_binding:
        if "bindings" not in policy:
            policy["bindings"] = []
        policy["bindings"].append({
            "role": role_to_add,
            "members": [member]
        })
        
    set_policy_url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:setIamPolicy"
    set_policy_data = {"policy": policy}
    set_policy_resp = requests.post(set_policy_url, headers=headers, json=set_policy_data)
    if set_policy_resp.status_code == 200:
        print("BigQuery Admin role granted successfully.")
    else:
        print(f"Error setting IAM policy: {set_policy_resp.text}")
        sys.exit(1)
        
    # Generate JSON key
    print("\nGenerating private key JSON keyfile...")
    key_url = f"https://iam.googleapis.com/v1/projects/{project_id}/serviceAccounts/{sa_email}/keys"
    key_resp = requests.post(key_url, headers=headers)
    if key_resp.status_code != 200:
        print(f"Error creating key: {key_resp.text}")
        sys.exit(1)
        
    key_data = key_resp.json()
    private_key_bytes = base64.b64decode(key_data["privateKeyData"])
    private_key_json = json.loads(private_key_bytes.decode("utf-8"))
    
    os.makedirs("data", exist_ok=True)
    credentials_path = os.path.join("data", "gcp_credentials.json")
    with open(credentials_path, "w") as f:
        json.dump(private_key_json, f, indent=2)
    print(f"Private key saved locally to '{credentials_path}' (git-ignored).")
    
    # Upload key to GitHub secrets
    print("\nUploading JSON key to GitHub Secrets...")
    try:
        env = os.environ.copy()
        env["PATH"] = "C:\\Program Files\\Git\\cmd;" + env.get("PATH", "")
        
        # Check CLI status
        auth_check = subprocess.run(
            ['C:\\Program Files\\GitHub CLI\\gh.exe', 'auth', 'status'], 
            capture_output=True, text=True, env=env
        )
        if auth_check.returncode != 0:
            print("Error: GitHub CLI is not authenticated. Run 'gh auth login' first.")
            sys.exit(1)
            
        with open(credentials_path, 'r') as f:
            secret_content = f.read()
            
        secret_proc = subprocess.run(
            ['C:\\Program Files\\GitHub CLI\\gh.exe', 'secret', 'set', 'GCP_CREDENTIALS'],
            input=secret_content, text=True, capture_output=True, env=env
        )
        
        if secret_proc.returncode == 0:
            print("GitHub Secret 'GCP_CREDENTIALS' successfully updated.")
        else:
            print(f"GitHub Secret configuration failed: {secret_proc.stderr}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Subprocess call error during GitHub secret integration: {e}")
        sys.exit(1)
        
    print("\nGoogle Cloud IAM and GitHub secrets configuration complete.")

if __name__ == "__main__":
    main()
