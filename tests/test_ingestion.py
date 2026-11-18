"""
Tests for High-Performance Polars Ingestion Service.
"""

import os
from django.test import TestCase
from inventory_core.models import Product, Supplier, InventoryLevel, SalesHistory
from inventory_core.services.ingestion import PolarsDataIngestionService

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_data")


class PolarsIngestionTestCase(TestCase):
    def test_full_sample_ingestion_pipeline(self):
        # 1. Ingest Suppliers
        supp_csv = os.path.join(SAMPLE_DIR, "sample_suppliers.csv")
        supp_result = PolarsDataIngestionService.ingest_suppliers_csv(supp_csv)
        self.assertEqual(supp_result["status"], "SUCCESS")
        self.assertGreater(Supplier.objects.count(), 0)

        # 2. Ingest Products
        prod_csv = os.path.join(SAMPLE_DIR, "sample_products.csv")
        prod_result = PolarsDataIngestionService.ingest_products_csv(prod_csv)
        self.assertEqual(prod_result["status"], "SUCCESS")
        self.assertGreater(Product.objects.count(), 0)

        # 3. Ingest Inventory
        inv_csv = os.path.join(SAMPLE_DIR, "sample_inventory.csv")
        inv_result = PolarsDataIngestionService.ingest_inventory_csv(inv_csv)
        self.assertEqual(inv_result["status"], "SUCCESS")
        self.assertGreater(InventoryLevel.objects.count(), 0)

        # 4. Ingest Sales History
        sales_csv = os.path.join(SAMPLE_DIR, "sample_sales_history.csv")
        sales_result = PolarsDataIngestionService.ingest_sales_history_csv(sales_csv)
        self.assertEqual(sales_result["status"], "SUCCESS")
        self.assertGreater(SalesHistory.objects.count(), 0)
