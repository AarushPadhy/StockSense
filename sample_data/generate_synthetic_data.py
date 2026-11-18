"""
Synthetic Data Generator for Supply Chain & Inventory Optimization Platform.
Generates realistic CSV datasets for Suppliers, Products, Inventory, and Time-Series Sales.
"""

import os
import csv
import random
from datetime import datetime, timedelta

SAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))

SUPPLIERS = [
    {"name": "Shenzhen MicroElectronics Ltd", "contact_email": "ops@sz-micro.cn", "region": "APAC", "lead_time_days": 18, "risk_score": 0.25, "reliability_rating": 0.94},
    {"name": "Bavaria Precision Sensors GmbH", "contact_email": "vertrieb@bavaria-sensors.de", "region": "EMEA", "lead_time_days": 12, "risk_score": 0.10, "reliability_rating": 0.98},
    {"name": "Pacific Rim Logistics & Fab", "contact_email": "supply@pacrim-fab.tw", "region": "APAC", "lead_time_days": 21, "risk_score": 0.45, "reliability_rating": 0.88},
    {"name": "NorthStar Industrial Optics", "contact_email": "orders@northstar-optics.com", "region": "NA", "lead_time_days": 7, "risk_score": 0.08, "reliability_rating": 0.99},
    {"name": "Nordic Polymer Compounds AB", "contact_email": "nordic@polymer-ab.se", "region": "EMEA", "lead_time_days": 14, "risk_score": 0.15, "reliability_rating": 0.96},
]

PRODUCTS = [
    {"sku": "SKU-ELEC-1001", "name": "ARM Cortex-M4 Microcontroller", "category": "Semiconductors", "unit_cost": 4.50, "unit_price": 12.00, "baseline_rop": 250, "moq": 100, "supplier": "Shenzhen MicroElectronics Ltd", "init_stock": 80, "safety": 50},
    {"sku": "SKU-ELEC-1002", "name": "High-Efficiency Power MOSFET 60V", "category": "Power Electronics", "unit_cost": 1.20, "unit_price": 3.80, "baseline_rop": 500, "moq": 200, "supplier": "Pacific Rim Logistics & Fab", "init_stock": 650, "safety": 100},
    {"sku": "SKU-SENS-2001", "name": "Precision MEMS Accelerometer 3-Axis", "category": "Sensors", "unit_cost": 8.75, "unit_price": 24.50, "baseline_rop": 150, "moq": 50, "supplier": "Bavaria Precision Sensors GmbH", "init_stock": 25, "safety": 30},
    {"sku": "SKU-SENS-2002", "name": "Infrared Thermal Pyrometer Sensor", "category": "Sensors", "unit_cost": 16.00, "unit_price": 45.00, "baseline_rop": 80, "moq": 20, "supplier": "Bavaria Precision Sensors GmbH", "init_stock": 110, "safety": 20},
    {"sku": "SKU-OPTI-3001", "name": "Telecentric Machine Vision Lens 50mm", "category": "Optics", "unit_cost": 120.00, "unit_price": 310.00, "baseline_rop": 30, "moq": 5, "supplier": "NorthStar Industrial Optics", "init_stock": 8, "safety": 5},
    {"sku": "SKU-POLY-4001", "name": "Thermally Conductive Epoxy Resin 5L", "category": "Materials", "unit_cost": 42.00, "unit_price": 95.00, "baseline_rop": 60, "moq": 10, "supplier": "Nordic Polymer Compounds AB", "init_stock": 75, "safety": 15},
    {"sku": "SKU-COMM-5001", "name": "Industrial Gigabit Ethernet Transceiver", "category": "Networking", "unit_cost": 9.50, "unit_price": 28.00, "baseline_rop": 120, "moq": 40, "supplier": "Shenzhen MicroElectronics Ltd", "init_stock": 15, "safety": 25},
]


def generate_all():
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    random.seed(42)

    # 1. Suppliers CSV
    supp_path = os.path.join(SAMPLE_DIR, "sample_suppliers.csv")
    with open(supp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "contact_email", "region", "lead_time_days", "risk_score", "reliability_rating"])
        for s in SUPPLIERS:
            writer.writerow([s["name"], s["contact_email"], s["region"], s["lead_time_days"], s["risk_score"], s["reliability_rating"]])
    print(f"Generated: {supp_path}")

    # 2. Products CSV
    prod_path = os.path.join(SAMPLE_DIR, "sample_products.csv")
    with open(prod_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "category", "unit_cost", "unit_price", "baseline_rop", "minimum_order_qty"])
        for p in PRODUCTS:
            writer.writerow([p["sku"], p["name"], p["category"], p["unit_cost"], p["unit_price"], p["baseline_rop"], p["moq"]])
    print(f"Generated: {prod_path}")

    # 3. Inventory CSV
    inv_path = os.path.join(SAMPLE_DIR, "sample_inventory.csv")
    with open(inv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "current_stock", "allocated_stock", "safety_stock", "supplier_name"])
        for p in PRODUCTS:
            allocated = int(p["init_stock"] * 0.15)
            writer.writerow([p["sku"], p["init_stock"], allocated, p["safety"], p["supplier"]])
    print(f"Generated: {inv_path}")

    # 4. Sales History CSV (90 days of time-series sales)
    sales_path = os.path.join(SAMPLE_DIR, "sample_sales_history.csv")
    base_date = datetime.now() - timedelta(days=90)
    sales_channels = ["ONLINE_DIRECT", "B2B_PORTAL", "DISTRIBUTOR_EDI"]

    with open(sales_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "recorded_at", "quantity_sold", "unit_selling_price", "sales_channel"])
        for day in range(90):
            current_day = base_date + timedelta(days=day)
            for p in PRODUCTS:
                # Add seasonality and random variance
                weekday_factor = 1.3 if current_day.weekday() < 5 else 0.7
                base_daily = max(1, p["baseline_rop"] // 25)
                # Introduce slight upward growth trend for first product to test Demand Agent
                trend_factor = 1.0 + (day / 90.0) * 0.4 if p["sku"] == "SKU-ELEC-1001" else 1.0
                qty = max(0, int(random.gauss(base_daily * weekday_factor * trend_factor, base_daily * 0.3)))
                
                if qty > 0:
                    dt_str = current_day.strftime("%Y-%m-%d 14:00:00")
                    channel = random.choice(sales_channels)
                    writer.writerow([p["sku"], dt_str, qty, p["unit_price"], channel])
    print(f"Generated: {sales_path}")


if __name__ == "__main__":
    generate_all()
