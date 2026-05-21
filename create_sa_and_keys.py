import os
import sys
import json
import base64
import subprocess
import pydata_google_auth
import google.auth.transport.requests

def main():
    print("=" * 80)
    print(" 🚀 AUTOMATED GOOGLE GCP SERVICE ACCOUNT & GITHUB SECRETS CREATOR 🚀 ")
    print("=" * 80)
    print("This utility script uses your local Google browser login to automatically:")
    print("1. Create a service account named 'github-actions-bq' in Google Cloud.")
    print("2. Grant the service account the BigQuery Admin role.")
    print("3. Generate and download the secure JSON private key.")
    print("4. Upload the key securely as a GitHub Repository Secret ('GCP_CREDENTIALS').\n")
    
    # 1. Get Project ID
    project_id = os.environ.get("GCP_PROJECT_ID", "").strip()
    if not project_id:
        project_id = input("👉 Enter your Google Cloud Project ID: ").strip()
    if not project_id:
        print("❌ Error: Project ID cannot be empty.")
        sys.exit(1)
        
    print("\n🔐 Authenticating with Google Cloud Platform...")
    try:
        credentials = pydata_google_auth.get_user_credentials(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
            auth_local_webserver=True
        )
        # Refresh credential to get access token
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        token = credentials.token
    except Exception as e:
        print(f"❌ Auth Error: {e}")
        sys.exit(1)
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id
    }
    
    sa_name = "github-actions-bq"
    sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"
    
    # 2. Create Service Account
    print(f"\n⏳ 1. Creating Service Account '{sa_name}' in GCP...")
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
        print(" -> [OK] Service Account created successfully.")
    elif resp.status_code == 409:
        print(" -> [OK] Service Account already exists.")
    else:
        print(f"❌ Error creating Service Account: {resp.text}")
        sys.exit(1)
        
    # 3. Grant BigQuery Admin Role
    print("\n⏳ 2. Granting BigQuery Admin role to the Service Account...")
    policy_url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:getIamPolicy"
    policy_resp = requests.post(policy_url, headers=headers)
    if policy_resp.status_code != 200:
        print(f"❌ Error getting IAM policy: {policy_resp.text}")
        print("💡 Tip: If you get a 403, make sure your OAuth account is a Project Owner/Editor.")
        sys.exit(1)
        
    policy = policy_resp.json()
    
    # Add binding
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
        print(" -> [OK] BigQuery Admin role granted successfully.")
    else:
        print(f"❌ Error setting IAM policy: {set_policy_resp.text}")
        sys.exit(1)
        
    # 4. Create and Download Service Account Key
    print("\n⏳ 3. Generating JSON private key...")
    key_url = f"https://iam.googleapis.com/v1/projects/{project_id}/serviceAccounts/{sa_email}/keys"
    key_resp = requests.post(key_url, headers=headers)
    if key_resp.status_code != 200:
        print(f"❌ Error creating key: {key_resp.text}")
        sys.exit(1)
        
    key_data = key_resp.json()
    private_key_bytes = base64.b64decode(key_data["privateKeyData"])
    private_key_json = json.loads(private_key_bytes.decode("utf-8"))
    
    os.makedirs("data", exist_ok=True)
    credentials_path = os.path.join("data", "gcp_credentials.json")
    with open(credentials_path, "w") as f:
        json.dump(private_key_json, f, indent=2)
    print(f" -> [OK] Private key saved securely at '{credentials_path}' (git-ignored).")
    
    # 5. Upload to GitHub Secrets
    print("\n⏳ 4. Uploading secret key to GitHub Secrets...")
    try:
        # Prepend Git path temporarily for subprocess
        env = os.environ.copy()
        env["PATH"] = "C:\\Program Files\\Git\\cmd;" + env.get("PATH", "")
        
        # Check GitHub CLI auth status
        auth_check = subprocess.run(
            ['C:\\Program Files\\GitHub CLI\\gh.exe', 'auth', 'status'], 
            capture_output=True, text=True, env=env
        )
        if auth_check.returncode != 0:
            print("❌ Error: GitHub CLI is not authenticated. Please log in first!")
            sys.exit(1)
            
        # Set GitHub Secret
        with open(credentials_path, 'r') as f:
            secret_content = f.read()
            
        secret_proc = subprocess.run(
            ['C:\\Program Files\\GitHub CLI\\gh.exe', 'secret', 'set', 'GCP_CREDENTIALS'],
            input=secret_content, text=True, capture_output=True, env=env
        )
        
        if secret_proc.returncode == 0:
            print(" -> [OK] GitHub Secret 'GCP_CREDENTIALS' successfully created!")
        else:
            print(f"❌ GitHub Secret Set Error: {secret_proc.stderr}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ System subprocess error during GitHub secret upload: {e}")
        sys.exit(1)
        
    print("\n" + "=" * 80)
    print("🎉 ALL CLOUD CONFIGURATIONS ARE 100% COMPLETE AND SECURED!")
    print("Your Service Account is created, authorized, and stored in GitHub Secrets!")
    print("=" * 80)

if __name__ == "__main__":
    main()
