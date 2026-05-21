import pytest
import pandas as pd
import numpy as np
from src.etl.etl_pipeline import EcomETL

@pytest.fixture
def etl_instance():
    """Returns an instance of EcomETL for helper testing."""
    return EcomETL(raw_data_dir="tests/mock_raw", processed_data_dir="tests/mock_processed")

def test_date_parsing_flexible(etl_instance):
    """Test standard and non-standard date format conversions."""
    dates = pd.Series(["2024-05-15", "12/25/2025", "2026-02-28", "invalid_date"])
    parsed_dates = etl_instance._parse_dates_flexibly(dates)
    
    # Assert successful standard conversion
    assert parsed_dates[0].year == 2024
    assert parsed_dates[0].month == 5
    assert parsed_dates[0].day == 15
    
    # Assert successful US format conversion
    assert parsed_dates[1].year == 2025
    assert parsed_dates[1].month == 12
    assert parsed_dates[1].day == 25
    
    # Assert invalid dates are mapped to NaT (Not a Time)
    assert pd.isna(parsed_dates[3])

def test_transform_products(etl_instance):
    """Test that dim_products removes negative prices and extreme outliers."""
    raw_products = pd.DataFrame({
        "product_id": ["PRD101", "PRD102", "PRD999", "PRD888"],
        "product_name": ["Laptop Pro", "  Chinos  ", "Demo Credit", "Enterprise Server"],
        "category": ["Electronics", "Apparel", "Electronics", "Electronics"],
        "base_price": [899.99, 45.00, -50.00, 99999.00]  # Standard, standard, negative, extreme
    })
    
    # Prepare dummy empty dataframes for others to avoid key errors in logic
    raw_customers = pd.DataFrame(columns=["customer_id", "full_name", "email", "country", "signup_date"])
    raw_orders = pd.DataFrame(columns=["order_id", "customer_id", "order_date", "status", "shipping_fee"])
    raw_items = pd.DataFrame(columns=["order_item_id", "order_id", "product_id", "quantity", "unit_price"])
    raw_sessions = pd.DataFrame(columns=[
        "session_id", "customer_id", "session_date", "traffic_source", 
        "device_type", "pages_viewed", "duration_seconds", "bounced", "converted"
    ])
    
    # Run transformation logic specifically for products
    etl_instance.transform_data(raw_customers, raw_products, raw_orders, raw_items, raw_sessions)
    
    dim_products = etl_instance.dim_products
    
    # We expect PRD101 and PRD102 to be kept, but PRD999 (negative) and PRD888 (outlier price > 5000) to be filtered out
    assert len(dim_products) == 2
    assert "PRD101" in dim_products["product_id"].values
    assert "PRD102" in dim_products["product_id"].values
    assert "PRD999" not in dim_products["product_id"].values
    assert "PRD888" not in dim_products["product_id"].values
    
    # Trim checks
    assert dim_products[dim_products["product_id"] == "PRD102"]["product_name"].values[0] == "Chinos"

def test_transform_customers(etl_instance):
    """Test customer deduplication, name casing, country standardizing, and date null handling."""
    raw_customers = pd.DataFrame({
        "customer_id": ["CUST101", "CUST101", "CUST102", "CUST103"], # Duplicate CUST101
        "full_name": ["  John Smith  ", "John Smith duplicate", "jane doe", ""], # Bad casing and empty
        "email": ["JOHN.SMITH@EXAMPLE.COM", "dup@example.com", "jane@example.com", None],
        "country": ["USA", "US", "Canada", "UK"], # USA/US country standardizing
        "signup_date": ["2024-01-15", "2024-01-15", "NULL", "10/31/2024"]
    })
    
    raw_products = pd.DataFrame(columns=["product_id", "product_name", "category", "base_price"])
    raw_orders = pd.DataFrame(columns=["order_id", "customer_id", "order_date", "status", "shipping_fee"])
    raw_items = pd.DataFrame(columns=["order_item_id", "order_id", "product_id", "quantity", "unit_price"])
    raw_sessions = pd.DataFrame(columns=[
        "session_id", "customer_id", "session_date", "traffic_source", 
        "device_type", "pages_viewed", "duration_seconds", "bounced", "converted"
    ])
    
    etl_instance.transform_data(raw_customers, raw_products, raw_orders, raw_items, raw_sessions)
    dim_cust = etl_instance.dim_customers
    
    # Count check: duplicate CUST101 removed, keeping first one (John Smith)
    assert len(dim_cust) == 3
    assert "CUST101" in dim_cust["customer_id"].values
    
    # Case cleaning check
    assert dim_cust[dim_cust["customer_id"] == "CUST101"]["full_name"].values[0] == "John Smith"
    assert dim_cust[dim_cust["customer_id"] == "CUST102"]["full_name"].values[0] == "Jane Doe"
    
    # Country mapping check
    assert dim_cust[dim_cust["customer_id"] == "CUST101"]["country"].values[0] == "United States"
    assert dim_cust[dim_cust["customer_id"] == "CUST103"]["country"].values[0] == "United Kingdom"
    
    # Email conversion to lowercase
    assert dim_cust[dim_cust["customer_id"] == "CUST101"]["email"].values[0] == "john.smith@example.com"

def test_transform_web_traffic(etl_instance):
    """Test clickstream sessions filtering of negative pages/durations, referential integrity check."""
    raw_customers = pd.DataFrame({
        "customer_id": ["CUST101", "CUST102"],
        "full_name": ["John Smith", "Jane Doe"],
        "email": ["john@example.com", "jane@example.com"],
        "country": ["United States", "Canada"],
        "signup_date": ["2024-01-15", "2024-02-15"]
    })
    raw_products = pd.DataFrame(columns=["product_id", "product_name", "category", "base_price"])
    raw_orders = pd.DataFrame(columns=["order_id", "customer_id", "order_date", "status", "shipping_fee"])
    raw_items = pd.DataFrame(columns=["order_item_id", "order_id", "product_id", "quantity", "unit_price"])
    
    raw_sessions = pd.DataFrame({
        "session_id": ["SESS001", "SESS002", "SESS003", "SESS004", "SESS005"],
        "customer_id": ["CUST101", "CUST102", "CUST999", "CUST101", "CUST102"],  # CUST999 is non-existent
        "session_date": ["2024-03-01", "2024-03-02", "2024-03-03", "2024-03-04", "2024-03-05"],
        "traffic_source": ["Google", "Direct", "Organic", "Social", "Email"],
        "device_type": ["Mobile", "Desktop", "Mobile", "Desktop", "Mobile"],
        "pages_viewed": [5, -2, 10, 4, 3],  # -2 pages viewed is anomaly
        "duration_seconds": [300, 120, 600, -10, 150],  # -10 duration is anomaly
        "bounced": [0, 0, 0, 1, 0],
        "converted": [1, 0, 1, 0, 0]
    })
    
    etl_instance.transform_data(raw_customers, raw_products, raw_orders, raw_items, raw_sessions)
    fact_web = etl_instance.fact_web_traffic
    
    # SESS001: Keep (valid)
    # SESS002: Drop (negative pages_viewed)
    # SESS003: Drop (orphan customer CUST999)
    # SESS004: Drop (negative duration_seconds)
    # SESS005: Keep (valid)
    
    assert len(fact_web) == 2
    assert "SESS001" in fact_web["session_id"].values
    assert "SESS005" in fact_web["session_id"].values
    assert "SESS002" not in fact_web["session_id"].values
    assert "SESS003" not in fact_web["session_id"].values
    assert "SESS004" not in fact_web["session_id"].values
