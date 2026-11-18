"""
Tests for Advanced Competitive Intelligence & Enterprise Features:
- Blue Yonder ABC-XYZ Stratification
- Resilinc TTS vs TTR Resilience
- Slimstock Wilson EOQ & Flexport ESG Carbon Footprint
- 1-Click Interactive Playbooks
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from inventory_core.models import Product, Supplier, InventoryLevel, PurchaseOrder
from inventory_core.services.analytics import SupplyChainAnalyticsService


class CompetitiveAnalyticsTestCase(APITestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="Advanced Fab Corp",
            region="APAC",
            lead_time_days=14,
            risk_score=0.20
        )
        self.product = Product.objects.create(
            sku="SKU-COMP-001",
            name="Industrial FPGA Core",
            category="Semiconductors",
            unit_cost=Decimal("75.00"),
            unit_price=Decimal("180.00"),
            baseline_rop=80,
            minimum_order_qty=20
        )
        self.inventory = InventoryLevel.objects.create(
            product=self.product,
            primary_supplier=self.supplier,
            current_stock=35,
            allocated_stock=5,
            safety_stock=20,
            days_of_stock_cover=Decimal("6.50"),
            stock_status=InventoryLevel.StockStatus.CRITICAL_STOCKOUT
        )

    def test_abc_xyz_stratification(self):
        data = SupplyChainAnalyticsService.calculate_abc_xyz_matrix()
        self.assertIn("stratified_products", data)
        self.assertIn("matrix_counts", data)
        self.assertGreater(len(data["stratified_products"]), 0)

        # Check API endpoint
        res = self.client.get(reverse('analytics-abc-xyz'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("stratified_products", res.data)

    def test_resilience_tts_vs_ttr(self):
        resilience = SupplyChainAnalyticsService.calculate_resilience_and_tts_ttr()
        self.assertIn("composite_resiliency_score", resilience)
        self.assertIn("sku_vulnerabilities", resilience)
        self.assertGreater(len(resilience["sku_vulnerabilities"]), 0)

        # Check API endpoint
        res = self.client.get(reverse('analytics-resilience-tts'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("composite_resiliency_score", res.data)

    def test_wilson_eoq_and_carbon(self):
        eoq = SupplyChainAnalyticsService.calculate_wilson_eoq_and_cost(self.product)
        self.assertGreater(eoq["recommended_eoq_units"], 0)
        self.assertGreater(eoq["total_annual_inventory_cost_usd"], 0)

        carbon = SupplyChainAnalyticsService.calculate_esg_carbon_emissions("APAC", 100)
        self.assertGreater(carbon["ocean_intermodal_co2_kg"], 0)
        self.assertGreater(carbon["expedited_air_co2_kg"], carbon["ocean_intermodal_co2_kg"])

        # Check API endpoint
        res = self.client.get(reverse('analytics-eoq') + f"?sku={self.product.sku}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("eoq_analysis", res.data)
        self.assertIn("esg_carbon_footprint", res.data)

    def test_playbook_execution(self):
        url = reverse('playbook-execute')

        # Test Playbook 1
        res1 = self.client.post(url, {"playbook": "port_strike_failover"}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertIn("playbook", res1.data)

        # Test Playbook 2
        res2 = self.client.post(url, {"playbook": "demand_surge_stress"}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertIn("data", res2.data)

        # Test Playbook 3
        res3 = self.client.post(url, {"playbook": "catalog_auto_pilot"}, format='json')
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertIn("auto_approved_orders_count", res3.data)
