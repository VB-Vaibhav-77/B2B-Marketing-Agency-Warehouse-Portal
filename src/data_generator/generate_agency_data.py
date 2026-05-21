import os
import csv
import random
import datetime
from datetime import timedelta

def generate_agency_data(output_dir="data/raw_agency"):
    os.makedirs(output_dir, exist_ok=True)
    random.seed(42)  # For deterministic data generation
    
    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2026, 4, 30)
    total_days = (end_date - start_date).days
    
    # 1. GENERATE DIM_ACCOUNT_MANAGERS
    managers = [
        {"manager_id": f"AM_{i:03d}", "name": name, "region": region, "target_monthly_revenue": target}
        for i, (name, region, target) in enumerate([
            ("Sarah Jenkins", "North America", 150000),
            ("Michael Chang", "APAC", 120000),
            ("Elena Rostova", "EMEA", 130000),
            ("David Cooper", "North America", 160000),
            ("Amina Yusuf", "EMEA", 110000),
            ("Carlos Ortiz", "LATAM", 90000),
            ("Jessica Taylor", "North America", 140000),
            ("Ryan Gallagher", "EMEA", 125000),
            ("Haruto Sato", "APAC", 100000),
            ("Chloe Laurent", "EMEA", 115000)
        ], 1)
    ]
    
    with open(os.path.join(output_dir, "managers.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["manager_id", "name", "region", "target_monthly_revenue"])
        writer.writeheader()
        writer.writerows(managers)
        
    # 2. GENERATE DIM_CLIENTS
    industries = ["B2B SaaS", "E-Commerce", "Fintech", "Healthcare", "Edtech", "Logistics", "Cybersecurity", "Web3"]
    tiers = ["Enterprise", "Mid-Market", "SMB"]
    
    clients = []
    client_ids = [f"CL_{i:03d}" for i in range(1, 101)]
    
    for cid in client_ids:
        industry = random.choice(industries)
        tier = random.choice(tiers)
        
        # Monthly retainer depends on tier
        if tier == "Enterprise":
            retainer = random.randint(15000, 45000)
        elif tier == "Mid-Market":
            retainer = random.randint(7000, 14000)
        else:
            retainer = random.randint(3000, 6000)
            
        onboard_days_offset = random.randint(0, total_days - 180) # Onboarded before last 6 months
        onboard_date = start_date + timedelta(days=onboard_days_offset)
        
        manager = random.choice(managers)
        
        clients.append({
            "client_id": cid,
            "company_name": f"ApexClient {cid[-3:]}",
            "industry": industry,
            "client_tier": tier,
            "monthly_retainer_fee": retainer,
            "onboarding_date": onboard_date.strftime("%Y-%m-%d"),
            "primary_account_manager_id": manager["manager_id"]
        })
        
    with open(os.path.join(output_dir, "clients.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["client_id", "company_name", "industry", "client_tier", "monthly_retainer_fee", "onboarding_date", "primary_account_manager_id"])
        writer.writeheader()
        writer.writerows(clients)

    # 3. GENERATE DIM_CAMPAIGNS
    channels = ["Google Ads", "Meta Ads", "LinkedIn Ads", "TikTok Ads", "YouTube Ads"]
    campaigns = []
    campaign_id_counter = 1
    
    for client in clients:
        # Each client runs 2 to 5 concurrent marketing campaigns
        num_campaigns = random.randint(2, 5)
        for _ in range(num_campaigns):
            channel = random.choice(channels)
            campaign_budget = random.randint(2000, 15000)
            
            campaigns.append({
                "campaign_id": f"CP_{campaign_id_counter:04d}",
                "client_id": client["client_id"],
                "campaign_name": f"CL_{client['client_id'][-3:]}_{channel.split()[0]}_{random.randint(1,3)}",
                "marketing_channel": channel,
                "monthly_ad_budget": campaign_budget
            })
            campaign_id_counter += 1
            
    with open(os.path.join(output_dir, "campaigns.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["campaign_id", "client_id", "campaign_name", "marketing_channel", "monthly_ad_budget"])
        writer.writeheader()
        writer.writerows(campaigns)

    # 4. GENERATE FACT_AD_PERFORMANCE
    # Daily advertising records for each campaign
    ad_performance = []
    
    # We generate daily metrics
    for day_offset in range(total_days):
        current_date = start_date + timedelta(days=day_offset)
        
        # We only generate performance for campaigns where their client was already onboarded
        for campaign in campaigns:
            client_id = campaign["client_id"]
            client_data = next(c for c in clients if c["client_id"] == client_id)
            onboard_date = datetime.datetime.strptime(client_data["onboarding_date"], "%Y-%m-%d").date()
            
            if current_date >= onboard_date:
                # Active campaign
                budget = campaign["monthly_ad_budget"]
                daily_budget = budget / 30.0
                
                # Introduce performance variance based on channel and day of week
                # Weekend discount on ads
                is_weekend = current_date.weekday() >= 5
                weekend_factor = 0.7 if is_weekend else 1.1
                
                spend = max(5.0, daily_budget * random.uniform(0.6, 1.4) * weekend_factor)
                
                # CPA and CTR changes by channel
                channel = campaign["marketing_channel"]
                if channel == "LinkedIn Ads":
                    ctr = random.uniform(0.005, 0.015)
                    cpc = random.uniform(3.50, 7.50)
                elif channel == "Google Ads":
                    ctr = random.uniform(0.02, 0.05)
                    cpc = random.uniform(1.20, 3.50)
                elif channel == "Meta Ads":
                    ctr = random.uniform(0.01, 0.03)
                    cpc = random.uniform(0.50, 1.80)
                else:  # TikTok/YouTube
                    ctr = random.uniform(0.015, 0.035)
                    cpc = random.uniform(0.30, 1.00)
                    
                # Clicks are driven by spend / CPC
                clicks = max(1, int(spend / cpc))
                impressions = int(clicks / ctr)
                
                # Conversion rate (leads or purchases generated for the client)
                conv_rate = random.uniform(0.02, 0.08)
                conversions = int(clicks * conv_rate)
                
                # Client revenue generated (estimated value of conversions)
                avg_deal_value = random.randint(50, 500)
                conversion_revenue = conversions * avg_deal_value * random.uniform(0.8, 1.2)
                
                ad_performance.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "campaign_id": campaign["campaign_id"],
                    "client_id": client_id,
                    "ad_spend": round(spend, 2),
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "client_conversion_revenue": round(conversion_revenue, 2)
                })
                
    with open(os.path.join(output_dir, "ad_performance.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "campaign_id", "client_id", "ad_spend", "impressions", "clicks", "conversions", "client_conversion_revenue"])
        writer.writeheader()
        writer.writerows(ad_performance)

    # 5. GENERATE FACT_CLIENT_BILLING
    # Monthly invoices billing the clients for retainer + campaign markups
    client_billing = []
    
    # We do billing on the 1st of every month
    current_month_date = start_date
    while current_month_date <= end_date:
        billing_date = current_month_date.replace(day=1)
        
        for client in clients:
            onboard_date = datetime.datetime.strptime(client["onboarding_date"], "%Y-%m-%d").date()
            # Invoice only if onboarded in or before this billing month
            if billing_date >= onboard_date.replace(day=1):
                retainer_fee = client["monthly_retainer_fee"]
                
                # Add ad management markup fee (15% of the client's ad spend from previous month)
                client_campaigns = [cp["campaign_id"] for cp in campaigns if cp["client_id"] == client["client_id"]]
                
                # Calculate estimated monthly ad spend for the client
                total_monthly_spend = sum(cp["monthly_ad_budget"] for cp in campaigns if cp["client_id"] == client["client_id"])
                management_fee = total_monthly_spend * 0.15
                
                # Add random variable hourly consulting fee
                consulting_hours = random.randint(5, 40)
                consulting_rate = 150.0
                consulting_fee = consulting_hours * consulting_rate
                
                billing_amount = retainer_fee + management_fee + consulting_fee
                
                client_billing.append({
                    "invoice_date": billing_date.strftime("%Y-%m-%d"),
                    "invoice_id": f"INV-{billing_date.year}{billing_date.month:02d}-{client['client_id'][-3:]}",
                    "client_id": client["client_id"],
                    "manager_id": client["primary_account_manager_id"],
                    "retainer_billing": round(retainer_fee, 2),
                    "ad_management_markup": round(management_fee, 2),
                    "consulting_billing": round(consulting_fee, 2),
                    "total_billing_amount": round(billing_amount, 2)
                })
                
        # Advance by 1 month
        if current_month_date.month == 12:
            current_month_date = current_month_date.replace(year=current_month_date.year + 1, month=1)
        else:
            current_month_date = current_month_date.replace(month=current_month_date.month + 1)
            
    with open(os.path.join(output_dir, "client_billing.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["invoice_date", "invoice_id", "client_id", "manager_id", "retainer_billing", "ad_management_markup", "consulting_billing", "total_billing_amount"])
        writer.writeheader()
        writer.writerows(client_billing)

    print(f"[SUCCESS] Raw B2B Agency Datasets generated successfully in '{output_dir}'!")

if __name__ == "__main__":
    generate_agency_data()
