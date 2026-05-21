import os
import sqlite3
import pytest
import pandas as pd
from src.etl.agency_etl import AgencyPipeline

@pytest.fixture
def mock_agency_data(tmp_path):
    """Generates small mock raw files in a temporary directory for unit testing."""
    raw_dir = tmp_path / "raw_agency"
    processed_dir = tmp_path / "processed_agency"
    db_path = tmp_path / "agency_analytics.db"
    
    raw_dir.mkdir()
    
    # 1. Create dim_account_managers mock data
    df_managers = pd.DataFrame({
        "manager_id": ["M1", "M2"],
        "name": ["  michael chang  ", "jane smith"],
        "region": ["APAC", "AMER"],
        "target_monthly_revenue": [500000.0, 300000.0]
    })
    
    # 2. Create dim_clients mock data
    df_clients = pd.DataFrame({
        "client_id": ["C1", "C2"],
        "company_name": ["  acme marketing agency corp  ", "globex corp"],
        "industry": ["Technology", "Healthcare"],
        "client_tier": ["Gold", "Silver"],
        "monthly_retainer_fee": [15000.0, 8000.0],
        "onboarding_date": ["2024-01-15", "2024-02-20"],
        "primary_account_manager_id": ["M1", "M2"]
    })
    
    # 3. Create dim_campaigns mock data
    df_campaigns = pd.DataFrame({
        "campaign_id": ["CAMP1", "CAMP2"],
        "client_id": ["C1", "C2"],
        "campaign_name": ["Search Ads", "Social Promo"],
        "marketing_channel": ["Google Ads", "Facebook Ads"],
        "monthly_ad_budget": [20000.0, 10000.0]
    })
    
    # 4. Create fact_ad_performance mock data
    df_ad_perf = pd.DataFrame({
        "date": ["2024-03-01", "2024-03-02"],
        "campaign_id": ["CAMP1", "CAMP2"],
        "client_id": ["C1", "C2"],
        "ad_spend": [1500.0, 800.0],
        "impressions": [50000, 20000],
        "clicks": [1200, 600],
        "conversions": [45, 18],
        "client_conversion_revenue": [12000.0, 4800.0]
    })
    
    # 5. Create fact_client_billing mock data
    df_billing = pd.DataFrame({
        "invoice_date": ["2024-03-31", "2024-03-31"],
        "invoice_id": ["INV001", "INV002"],
        "client_id": ["C1", "C2"],
        "manager_id": ["M1", "M2"],
        "retainer_billing": [15000.0, 8000.0],
        "ad_management_markup": [1500.0, 800.0],
        "consulting_billing": [500.0, 0.0],
        "total_billing_amount": [17000.0, 8800.0]
    })
    
    # Save as CSV files
    df_managers.to_csv(raw_dir / "managers.csv", index=False)
    df_clients.to_csv(raw_dir / "clients.csv", index=False)
    df_campaigns.to_csv(raw_dir / "campaigns.csv", index=False)
    df_ad_perf.to_csv(raw_dir / "ad_performance.csv", index=False)
    df_billing.to_csv(raw_dir / "client_billing.csv", index=False)
    
    return {
        "raw_dir": str(raw_dir),
        "processed_dir": str(processed_dir),
        "db_path": str(db_path)
    }

def test_agency_etl_cleaning(mock_agency_data):
    """Verify that name stripping and title casing are properly performed during B2B ETL."""
    pipeline = AgencyPipeline(
        raw_dir=mock_agency_data["raw_dir"],
        processed_dir=mock_agency_data["processed_dir"],
        db_path=mock_agency_data["db_path"]
    )
    
    pipeline.run_etl()
    
    # Verify CSV files are written
    assert os.path.exists(os.path.join(mock_agency_data["processed_dir"], "dim_clients.csv"))
    assert os.path.exists(os.path.join(mock_agency_data["processed_dir"], "dim_account_managers.csv"))
    
    # Read processed CSVs to verify string cleaning
    df_clients = pd.read_csv(os.path.join(mock_agency_data["processed_dir"], "dim_clients.csv"))
    df_managers = pd.read_csv(os.path.join(mock_agency_data["processed_dir"], "dim_account_managers.csv"))
    
    # Assert company_name was title-cased and stripped of leading/trailing spaces
    assert df_clients[df_clients["client_id"] == "C1"]["company_name"].values[0] == "Acme Marketing Agency Corp"
    
    # Assert manager name was title-cased and stripped
    assert df_managers[df_managers["manager_id"] == "M1"]["name"].values[0] == "Michael Chang"

def test_agency_db_loading(mock_agency_data):
    """Verify that tables are loaded into the SQLite B2B database correctly."""
    pipeline = AgencyPipeline(
        raw_dir=mock_agency_data["raw_dir"],
        processed_dir=mock_agency_data["processed_dir"],
        db_path=mock_agency_data["db_path"]
    )
    
    pipeline.run_etl()
    
    # Check SQLite DB content
    conn = sqlite3.connect(mock_agency_data["db_path"])
    
    df_db_clients = pd.read_sql_query("SELECT * FROM dim_clients", conn)
    df_db_billing = pd.read_sql_query("SELECT * FROM fact_client_billing", conn)
    
    assert len(df_db_clients) == 2
    assert "C1" in df_db_clients["client_id"].values
    assert df_db_billing[df_db_billing["invoice_id"] == "INV001"]["total_billing_amount"].values[0] == 17000.0
    
    conn.close()
