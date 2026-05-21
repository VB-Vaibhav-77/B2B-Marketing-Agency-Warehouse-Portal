import os
import sqlite3
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("Data_Validation")

class DataValidator:
    def __init__(self, db_path="data/apex_analytics.db"):
        self.db_path = db_path
        
    def run_validations(self):
        logger.info("Starting Data Quality & Integrity Validation...")
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}. Build database first!")
            
        conn = sqlite3.connect(self.db_path)
        
        validation_results = []
        all_passed = True
        
        def log_test(test_name, success, details):
            status = "PASSED" if success else "FAILED"
            emoji = "✅" if success else "❌"
            logger.info(f"{emoji} [{test_name}]: {status} - {details}")
            validation_results.append({
                "test_name": test_name,
                "status": status,
                "details": details
            })
            return success

        # ----------------------------------------------------
        # Test 1: Primary Key Null Checks
        # ----------------------------------------------------
        pk_queries = {
            "dim_customers.customer_id": "SELECT COUNT(*) FROM dim_customers WHERE customer_id IS NULL",
            "dim_products.product_id": "SELECT COUNT(*) FROM dim_products WHERE product_id IS NULL",
            "dim_date.date_key": "SELECT COUNT(*) FROM dim_date WHERE date_key IS NULL",
            "fact_sales.order_item_id": "SELECT COUNT(*) FROM fact_sales WHERE order_item_id IS NULL",
            "fact_web_traffic.session_id": "SELECT COUNT(*) FROM fact_web_traffic WHERE session_id IS NULL"
        }
        
        for field, query in pk_queries.items():
            df = pd.read_sql_query(query, conn)
            count = df.iloc[0, 0]
            success = (count == 0)
            if not log_test(f"Null Check: {field}", success, f"Found {count} null values in PK."):
                all_passed = False

        # ----------------------------------------------------
        # Test 2: Unique Key Check
        # ----------------------------------------------------
        unique_queries = {
            "dim_customers.customer_id": "SELECT COUNT(customer_id) - COUNT(DISTINCT customer_id) FROM dim_customers",
            "dim_products.product_id": "SELECT COUNT(product_id) - COUNT(DISTINCT product_id) FROM dim_products",
            "dim_date.date_key": "SELECT COUNT(date_key) - COUNT(DISTINCT date_key) FROM dim_date",
            "fact_sales.order_item_id": "SELECT COUNT(order_item_id) - COUNT(DISTINCT order_item_id) FROM fact_sales",
            "fact_web_traffic.session_id": "SELECT COUNT(session_id) - COUNT(DISTINCT session_id) FROM fact_web_traffic"
        }
        
        for field, query in unique_queries.items():
            df = pd.read_sql_query(query, conn)
            duplicates = df.iloc[0, 0]
            success = (duplicates == 0)
            if not log_test(f"Uniqueness Check: {field}", success, f"Found {duplicates} duplicate primary keys."):
                all_passed = False

        # ----------------------------------------------------
        # Test 3: Referential Integrity
        # ----------------------------------------------------
        ref_queries = {
            "fact_sales -> dim_customers": """
                SELECT COUNT(*) FROM fact_sales 
                WHERE customer_id NOT IN (SELECT customer_id FROM dim_customers)
            """,
            "fact_sales -> dim_products": """
                SELECT COUNT(*) FROM fact_sales 
                WHERE product_id NOT IN (SELECT product_id FROM dim_products)
            """,
            "fact_sales -> dim_date": """
                SELECT COUNT(*) FROM fact_sales 
                WHERE order_date NOT IN (SELECT date_key FROM dim_date)
            """,
            "fact_web_traffic -> dim_customers": """
                SELECT COUNT(*) FROM fact_web_traffic 
                WHERE customer_id NOT IN (SELECT customer_id FROM dim_customers)
            """,
            "fact_web_traffic -> dim_date": """
                SELECT COUNT(*) FROM fact_web_traffic 
                WHERE session_date NOT IN (SELECT date_key FROM dim_date)
            """
        }
        
        for relationship, query in ref_queries.items():
            df = pd.read_sql_query(query, conn)
            orphans = df.iloc[0, 0]
            success = (orphans == 0)
            if not log_test(f"Referential Integrity: {relationship}", success, f"Found {orphans} orphaned records."):
                all_passed = False

        # ----------------------------------------------------
        # Test 4: Positive Financial Metrics (Quantities and Prices)
        # ----------------------------------------------------
        financial_queries = {
            "fact_sales.quantity": "SELECT COUNT(*) FROM fact_sales WHERE quantity <= 0",
            "fact_sales.unit_price": "SELECT COUNT(*) FROM fact_sales WHERE unit_price <= 0",
            "dim_products.base_price": "SELECT COUNT(*) FROM dim_products WHERE base_price <= 0",
            "fact_web_traffic.pages_viewed": "SELECT COUNT(*) FROM fact_web_traffic WHERE pages_viewed <= 0",
            "fact_web_traffic.duration_seconds": "SELECT COUNT(*) FROM fact_web_traffic WHERE duration_seconds < 0",
            "fact_web_traffic.bounced (binary check)": "SELECT COUNT(*) FROM fact_web_traffic WHERE bounced NOT IN (0, 1)",
            "fact_web_traffic.converted (binary check)": "SELECT COUNT(*) FROM fact_web_traffic WHERE converted NOT IN (0, 1)"
        }
        
        for metric, query in financial_queries.items():
            df = pd.read_sql_query(query, conn)
            negatives = df.iloc[0, 0]
            success = (negatives == 0)
            if not log_test(f"Logical Value Check: {metric}", success, f"Found {negatives} records with negative or zero values."):
                all_passed = False

        # ----------------------------------------------------
        # Test 5: Calculation Accuracy (line_subtotal = quantity * unit_price)
        # ----------------------------------------------------
        calc_query = """
            SELECT COUNT(*) FROM fact_sales 
            WHERE ABS(line_subtotal - (quantity * unit_price)) > 0.01
        """
        df = pd.read_sql_query(calc_query, conn)
        diff_count = df.iloc[0, 0]
        success = (diff_count == 0)
        if not log_test("Calculation Check: line_subtotal", success, f"Found {diff_count} records where subtotal does not match qty * price."):
            all_passed = False
            
        conn.close()
        
        # Save Validation Report
        report_df = pd.DataFrame(validation_results)
        os.makedirs("data", exist_ok=True)
        report_df.to_csv("data/data_validation_report.csv", index=False)
        logger.info("Validation report written to: data/data_validation_report.csv")
        
        if all_passed:
            logger.info("🎉 DATA VALIDATION SUMMARY: 100% PASSED. Data quality is pristine!")
            return True
        else:
            logger.warning("⚠️ DATA VALIDATION SUMMARY: Some checks FAILED. Review report details!")
            return False

class AgencyDataValidator:
    def __init__(self, db_path="data/agency_analytics.db"):
        self.db_path = db_path
        
    def run_validations(self):
        logger.info("Starting B2B Agency Data Quality & Integrity Validation...")
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}. Build database first!")
            
        conn = sqlite3.connect(self.db_path)
        
        validation_results = []
        all_passed = True
        
        def log_test(test_name, success, details):
            status = "PASSED" if success else "FAILED"
            emoji = "✅" if success else "❌"
            logger.info(f"{emoji} [{test_name}]: {status} - {details}")
            validation_results.append({
                "test_name": test_name,
                "status": status,
                "details": details
            })
            return success

        # ----------------------------------------------------
        # Test Group 1: Primary Key Null Checks (6 tests)
        # ----------------------------------------------------
        pk_queries = {
            "dim_account_managers.manager_id": "SELECT COUNT(*) FROM dim_account_managers WHERE manager_id IS NULL",
            "dim_clients.client_id": "SELECT COUNT(*) FROM dim_clients WHERE client_id IS NULL",
            "dim_campaigns.campaign_id": "SELECT COUNT(*) FROM dim_campaigns WHERE campaign_id IS NULL",
            "dim_date.date_key": "SELECT COUNT(*) FROM dim_date WHERE date_key IS NULL",
            "fact_ad_performance.campaign_id": "SELECT COUNT(*) FROM fact_ad_performance WHERE campaign_id IS NULL OR date IS NULL",
            "fact_client_billing.invoice_id": "SELECT COUNT(*) FROM fact_client_billing WHERE invoice_id IS NULL"
        }
        
        for field, query in pk_queries.items():
            df = pd.read_sql_query(query, conn)
            count = df.iloc[0, 0]
            success = (count == 0)
            if not log_test(f"Null Check: {field}", success, f"Found {count} null values in PK."):
                all_passed = False

        # ----------------------------------------------------
        # Test Group 2: Unique Key Check (5 tests)
        # ----------------------------------------------------
        unique_queries = {
            "dim_account_managers.manager_id": "SELECT COUNT(manager_id) - COUNT(DISTINCT manager_id) FROM dim_account_managers",
            "dim_clients.client_id": "SELECT COUNT(client_id) - COUNT(DISTINCT client_id) FROM dim_clients",
            "dim_campaigns.campaign_id": "SELECT COUNT(campaign_id) - COUNT(DISTINCT campaign_id) FROM dim_campaigns",
            "dim_date.date_key": "SELECT COUNT(date_key) - COUNT(DISTINCT date_key) FROM dim_date",
            "fact_client_billing.invoice_id": "SELECT COUNT(invoice_id) - COUNT(DISTINCT invoice_id) FROM fact_client_billing"
        }
        
        for field, query in unique_queries.items():
            df = pd.read_sql_query(query, conn)
            duplicates = df.iloc[0, 0]
            success = (duplicates == 0)
            if not log_test(f"Uniqueness Check: {field}", success, f"Found {duplicates} duplicate primary keys."):
                all_passed = False

        # ----------------------------------------------------
        # Test Group 3: Referential Integrity (6 tests)
        # ----------------------------------------------------
        ref_queries = {
            "dim_clients -> dim_account_managers": """
                SELECT COUNT(*) FROM dim_clients 
                WHERE primary_account_manager_id NOT IN (SELECT manager_id FROM dim_account_managers)
            """,
            "dim_campaigns -> dim_clients": """
                SELECT COUNT(*) FROM dim_campaigns 
                WHERE client_id NOT IN (SELECT client_id FROM dim_clients)
            """,
            "fact_ad_performance -> dim_date": """
                SELECT COUNT(*) FROM fact_ad_performance 
                WHERE date NOT IN (SELECT date_key FROM dim_date)
            """,
            "fact_ad_performance -> dim_campaigns": """
                SELECT COUNT(*) FROM fact_ad_performance 
                WHERE campaign_id NOT IN (SELECT campaign_id FROM dim_campaigns)
            """,
            "fact_client_billing -> dim_clients": """
                SELECT COUNT(*) FROM fact_client_billing 
                WHERE client_id NOT IN (SELECT client_id FROM dim_clients)
            """,
            "fact_client_billing -> dim_account_managers": """
                SELECT COUNT(*) FROM fact_client_billing 
                WHERE manager_id NOT IN (SELECT manager_id FROM dim_account_managers)
            """
        }
        
        for relationship, query in ref_queries.items():
            df = pd.read_sql_query(query, conn)
            orphans = df.iloc[0, 0]
            success = (orphans == 0)
            if not log_test(f"Referential Integrity: {relationship}", success, f"Found {orphans} orphaned records."):
                all_passed = False

        # ----------------------------------------------------
        # Test Group 4: Logical / Financial Value Checks (5 tests)
        # ----------------------------------------------------
        financial_queries = {
            "dim_account_managers.target_monthly_revenue": "SELECT COUNT(*) FROM dim_account_managers WHERE target_monthly_revenue < 0",
            "dim_clients.monthly_retainer_fee": "SELECT COUNT(*) FROM dim_clients WHERE monthly_retainer_fee < 0",
            "dim_campaigns.monthly_ad_budget": "SELECT COUNT(*) FROM dim_campaigns WHERE monthly_ad_budget < 0",
            "fact_ad_performance.ad_spend": "SELECT COUNT(*) FROM fact_ad_performance WHERE ad_spend < 0",
            "fact_client_billing.total_billing_amount": "SELECT COUNT(*) FROM fact_client_billing WHERE total_billing_amount < 0"
        }
        
        for metric, query in financial_queries.items():
            df = pd.read_sql_query(query, conn)
            negatives = df.iloc[0, 0]
            success = (negatives == 0)
            if not log_test(f"Logical Value Check: {metric}", success, f"Found {negatives} records with negative values."):
                all_passed = False

        # ----------------------------------------------------
        # Test Group 5: Calculation Accuracy (1 test)
        # ----------------------------------------------------
        calc_query = """
            SELECT COUNT(*) FROM fact_client_billing 
            WHERE ABS(total_billing_amount - (retainer_billing + ad_management_markup + consulting_billing)) > 0.01
        """
        df = pd.read_sql_query(calc_query, conn)
        diff_count = df.iloc[0, 0]
        success = (diff_count == 0)
        if not log_test("Calculation Check: billing_sum", success, f"Found {diff_count} records where total billing does not match sum of details."):
            all_passed = False
            
        conn.close()
        
        # Save B2B Validation Report
        report_df = pd.DataFrame(validation_results)
        os.makedirs("data", exist_ok=True)
        report_df.to_csv("data/agency_validation_report.csv", index=False)
        logger.info("Agency validation report written to: data/agency_validation_report.csv")
        
        if all_passed:
            logger.info("🎉 B2B AGENCY DATA VALIDATION: 100% PASSED. Data quality is pristine!")
            return True
        else:
            logger.warning("⚠️ B2B AGENCY DATA VALIDATION: Some checks FAILED. Review report details!")
            return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "agency":
        validator = AgencyDataValidator()
        validator.run_validations()
    else:
        validator = DataValidator()
        validator.run_validations()
