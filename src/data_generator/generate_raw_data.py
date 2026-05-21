import os
import random
import csv
from datetime import datetime, timedelta

def generate_data(output_dir="data/raw"):
    os.makedirs(output_dir, exist_ok=True)
    random.seed(42)  # For reproducible results
    
    print(f"Generating synthetic e-commerce and web traffic raw data in: {output_dir}")
    
    # ----------------------------------------------------
    # Configuration
    # ----------------------------------------------------
    num_customers = 1000
    num_products = 50
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 5, 1)
    
    # ----------------------------------------------------
    # 1. GENERATE PRODUCTS (with some anomalies)
    # ----------------------------------------------------
    categories = {
        "Electronics": ["Smartphone x10", "Laptop Pro 15", "Wireless Earbuds", "Smart Watch v2", "4K Monitor 27", "Bluetooth Speaker"],
        "Apparel": ["Classic Denim Jacket", "Slim Fit Chinos", "Activewear Tee", "Wool Knit Sweater", "Running Shoes", "Leather Belt"],
        "Home & Kitchen": ["Air Fryer XL", "Drip Coffee Maker", "Memory Foam Pillow", "Stainless Cookware", "Robot Vacuum", "Ceramic Mug Set"],
        "Sports & Outdoors": ["Yoga Mat Non-Slip", "Water Bottle 32oz", "Camping Tent 4-Person", "Adjustable Dumbbells", "Cycling Helmet"]
    }
    
    products = []
    product_idx = 100
    for category, items in categories.items():
        for item in items:
            product_idx += 1
            prod_id = f"PRD{product_idx}"
            
            if category == "Electronics":
                base_price = round(random.uniform(99.00, 1200.00), 2)
            elif category == "Apparel":
                base_price = round(random.uniform(19.00, 150.00), 2)
            elif category == "Home & Kitchen":
                base_price = round(random.uniform(25.00, 350.00), 2)
            else:
                base_price = round(random.uniform(15.00, 250.00), 2)
                
            products.append({
                "product_id": prod_id,
                "product_name": item,
                "category": category,
                "base_price": base_price
            })
            
    products.append({
        "product_id": "PRD999",
        "product_name": "Demo Return Credit",
        "category": "Electronics",
        "base_price": -50.00
    })
    products.append({
        "product_id": "PRD888",
        "product_name": "Premium Enterprise Server",
        "category": "Electronics",
        "base_price": 99999.99
    })
    
    # Write Products CSV
    prod_file = os.path.join(output_dir, "products_raw.csv")
    with open(prod_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "product_name", "category", "base_price"])
        writer.writeheader()
        writer.writerows(products)
    print(f"Generated {len(products)} products at {prod_file}")
    
    # ----------------------------------------------------
    # 2. GENERATE CUSTOMERS (with dirty text & date formats)
    # ----------------------------------------------------
    first_names = ["John", "Jane", "Michael", "Emily", "David", "Sarah", "James", "Jessica", "Robert", "Ashley", "William", "Amanda", "Joseph", "Melissa", "Charles", "Stephanie", "Thomas", "Nicole", "Daniel", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    countries = ["United States", "USA", "US", "Canada", "United Kingdom", "UK", "Germany", "France", "Australia"]
    
    customers = []
    signup_dates = {}
    
    for i in range(1, num_customers + 1):
        cust_id = f"CUST{1000 + i}"
        days_range = (end_date - start_date).days
        signup_offset = int((random.random() ** 1.5) * days_range)
        signup_dt = start_date + timedelta(days=signup_offset)
        signup_dates[cust_id] = signup_dt
        
        first = random.choice(first_names)
        last = random.choice(last_names)
        
        full_name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@example.com"
        country = random.choice(countries)
        
        date_format_choice = random.choice(["iso", "us", "iso", "iso"])
        if i % 100 == 0:
            signup_str = "202-01-01" if i % 200 == 0 else "NULL"
        elif date_format_choice == "us":
            signup_str = signup_dt.strftime("%m/%d/%Y")
        else:
            signup_str = signup_dt.strftime("%Y-%m-%d")
            
        if i % 15 == 0:
            full_name = f"  {full_name}   "
        if i % 20 == 0:
            full_name = full_name.lower()
            
        if i % 70 == 0:
            full_name = ""
        if i % 95 == 0:
            email = ""
            
        customers.append({
            "customer_id": cust_id,
            "full_name": full_name,
            "email": email,
            "country": country,
            "signup_date": signup_str
        })
        
    customers.append({
        "customer_id": "CUST1001",
        "full_name": "John Smith (Duplicate Entry)",
        "email": "john.smith99@example.com",
        "country": "United States",
        "signup_date": "2024-01-01"
    })
    
    cust_file = os.path.join(output_dir, "customers_raw.csv")
    with open(cust_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["customer_id", "full_name", "email", "country", "signup_date"])
        writer.writeheader()
        writer.writerows(customers)
    print(f"Generated {len(customers)} raw customers at {cust_file}")
    
    # ----------------------------------------------------
    # 3. GENERATE ORDERS & SESSIONS (Multi-Fact Alignment)
    # ----------------------------------------------------
    orders = []
    order_items = []
    sessions = []
    
    order_id_counter = 5000
    order_item_id_counter = 20000
    session_id_counter = 40000
    
    statuses = ["Completed", "Completed", "Completed", "Completed", "Pending", "Cancelled", "Returned"]
    sources = ["Organic Search", "Direct", "Paid Google Ads", "Social Media", "Referral", "Paid Ads"]
    devices = ["Desktop", "Mobile", "Mobile", "Tablet"]
    
    for cust in customers:
        cust_id = cust["customer_id"]
        if cust_id not in signup_dates:
            continue
            
        c_signup = signup_dates[cust_id]
        
        # Determine engagement levels
        loyalty = random.choice(["one-time", "standard", "loyal", "loyal"])
        if loyalty == "one-time":
            num_sessions = random.randint(1, 3)
            num_purchases = 1
        elif loyalty == "standard":
            num_sessions = random.randint(3, 8)
            num_purchases = random.randint(1, 3)
        else:  # loyal
            num_sessions = random.randint(8, 25)
            num_purchases = random.randint(3, 12)
            
        # Create website sessions (including conversions and bounces)
        current_time = c_signup
        purchase_dates = []
        
        # 3a. Generate Sessions
        for s in range(num_sessions):
            if current_time >= end_date:
                break
                
            days_to_session = int(random.expovariate(1.0 / 15)) + 1  # Mean 15 days
            current_time += timedelta(days=days_to_session)
            if current_time >= end_date:
                break
                
            session_id_counter += 1
            sess_id = f"SES{session_id_counter}"
            
            traffic_source = random.choice(sources)
            device_type = random.choice(devices)
            
            # Engagement metrics
            pages_viewed = random.randint(1, 15)
            duration_seconds = pages_viewed * random.randint(20, 90)
            
            # Anomaly injection: Negative session duration
            if session_id_counter % 350 == 0:
                duration_seconds = -30
                
            bounced = 1 if pages_viewed == 1 else 0
            
            # Determine if this session converted (loyal customers convert more frequently)
            converted = 0
            if not bounced and len(purchase_dates) < num_purchases:
                # 30% chance of conversion if pages viewed is high
                if pages_viewed > 5 and random.random() < 0.4:
                    converted = 1
                    purchase_dates.append(current_time)
                    
            # Inconsistent Date Formats in sessions
            date_format_choice = random.choice(["iso", "iso", "us"])
            session_date_str = current_time.strftime("%m/%d/%Y") if date_format_choice == "us" else current_time.strftime("%Y-%m-%d")
            
            sessions.append({
                "session_id": sess_id,
                "customer_id": cust_id,
                "session_date": session_date_str,
                "traffic_source": traffic_source,
                "device_type": device_type,
                "pages_viewed": pages_viewed,
                "duration_seconds": duration_seconds,
                "bounced": bounced,
                "converted": converted
            })
            
        # 3b. Generate corresponding Orders for the converted sessions
        for p_date in purchase_dates:
            order_id_counter += 1
            order_id = f"ORD{order_id_counter}"
            status = random.choice(statuses)
            shipping_fee = round(random.choice([0.00, 4.99, 9.99, 14.99]), 2)
            
            date_format_choice = random.choice(["iso", "iso", "us"])
            order_date_str = p_date.strftime("%m/%d/%Y") if date_format_choice == "us" else p_date.strftime("%Y-%m-%d")
            
            items_in_order = random.randint(1, 4)
            order_has_active_items = False
            
            for _ in range(items_in_order):
                prod = random.choice(products)
                if prod["product_id"] in ["PRD999", "PRD888"] and random.random() > 0.05:
                    continue
                        
                order_item_id_counter += 1
                item_id = f"ITM{order_item_id_counter}"
                quantity = random.choices([1, 2, 3, 4], weights=[70, 20, 7, 3])[0]
                
                # Anomalies
                if order_item_id_counter % 250 == 0:
                    quantity = -1
                    
                order_items.append({
                    "order_item_id": item_id,
                    "order_id": order_id,
                    "product_id": prod["product_id"],
                    "quantity": quantity,
                    "unit_price": prod["base_price"]
                })
                order_has_active_items = True
                
            if order_has_active_items:
                orders.append({
                    "order_id": order_id,
                    "customer_id": cust_id,
                    "order_date": order_date_str,
                    "status": status,
                    "shipping_fee": shipping_fee
                })
                
    # Write Orders CSV
    ord_file = os.path.join(output_dir, "orders_raw.csv")
    with open(ord_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["order_id", "customer_id", "order_date", "status", "shipping_fee"])
        writer.writeheader()
        writer.writerows(orders)
    print(f"Generated {len(orders)} raw orders at {ord_file}")
    
    # Write Order Items CSV
    items_file = os.path.join(output_dir, "order_items_raw.csv")
    with open(items_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["order_item_id", "order_id", "product_id", "quantity", "unit_price"])
        writer.writeheader()
        writer.writerows(order_items)
    print(f"Generated {len(order_items)} raw order items at {items_file}")
    
    # Write Website Sessions CSV
    sess_file = os.path.join(output_dir, "sessions_raw.csv")
    with open(sess_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["session_id", "customer_id", "session_date", "traffic_source", "device_type", "pages_viewed", "duration_seconds", "bounced", "converted"])
        writer.writeheader()
        writer.writerows(sessions)
    print(f"Generated {len(sessions)} raw website sessions at {sess_file}")
    
    print("Raw synthetic e-commerce and web traffic data generation complete.")

if __name__ == "__main__":
    generate_data()
