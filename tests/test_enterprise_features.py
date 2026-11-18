"""
Unit & Integration Tests for Enterprise Supply Chain Features:
1. Supplier Scorecard & OTIF Engine
2. Landed Cost & Customs Tariff Optimizer
3. Bullwhip (Forrester Effect) Suppression
4. Shelf-Life Obsolescence Monitor
5. ANSI X12 EDI 850 Generator
"""

from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from inventory_core.models import Product, Supplier, InventoryLevel, PurchaseOrder
from inventory_core.services.supplier_scorecard import SupplierScorecardService
from inventory_core.services.landed_cost import LandedCostService
from inventory_core.services.bullwhip import BullwhipSuppressionService
from inventory_core.services.obsolescence import ObsolescenceMonitorService
from inventory_core.services.edi_generator import EDIGeneratorService


class EnterpriseFeaturesTestCase(APITestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="Shenzhen Micro Precision",
            region="APAC",
            lead_time_days=18,
            risk_score=0.15,
            reliability_rating=0.96
        )
        self.product = Product.objects.create(
            sku="SKU-ENT-001",
            name="Aerospace Controller Module",
            category="Semiconductors",
            unit_cost=Decimal("50.00"),
            unit_price=Decimal("120.00"),
            baseline_rop=100,
            minimum_order_qty=20
        )
        self.inventory = InventoryLevel.objects.create(
            product=self.product,
            primary_supplier=self.supplier,
            current_stock=250,
            allocated_stock=20,
            safety_stock=30,
            days_of_stock_cover=Decimal("400.00"),  # Exceeds shelf-life of 365d -> triggers obsolescence
            stock_status=InventoryLevel.StockStatus.OVERSTOCKED
        )
        self.po = PurchaseOrder.objects.create(
            po_number="PO-EDI-TEST-001",
            supplier=self.supplier,
            product=self.product,
            quantity=100,
            unit_cost=Decimal("50.00"),
            status=PurchaseOrder.POStatus.APPROVED,
            ai_reasoning="Procurement authorized via autonomous replenishment."
        )

    def test_supplier_scorecard(self):
        card = SupplierScorecardService.evaluate_supplier(self.supplier)
        self.assertGreater(card["otif_delivery_percentage"], 80.0)
        self.assertIn("vendor_tier", card)
        self.assertEqual(card["contract_lead_time_days"], 18)

        # Test endpoint
        res = self.client.get(reverse('supplier-scorecards-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreater(res.data["count"], 0)

    def test_landed_cost_calculation(self):
        landed = LandedCostService.calculate_landed_cost(self.product, self.supplier, 100)
        self.assertEqual(landed["supplier_region"], "APAC")
        self.assertGreater(landed["cost_breakdown_per_unit"]["total_landed_cost"], 50.00)
        self.assertGreater(landed["financial_totals"]["total_landed_liability_usd"], 5000.00)

        # Test corridor comparison endpoint
        res = self.client.get(reverse('analytics-landed-cost') + f"?sku={self.product.sku}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("cheapest_landed_option", res.data)

    def test_bullwhip_effect_analysis(self):
        bw = BullwhipSuppressionService.analyze_bullwhip_effect(self.product)
        self.assertIn("bullwhip_ratio", bw)
        self.assertIn("severity", bw)
        self.assertGreater(bw["smoothed_order_qty"], 0)

        # Test endpoint
        res = self.client.get(reverse('analytics-bullwhip') + f"?sku={self.product.sku}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("bullwhip_ratio", res.data)

    def test_obsolescence_monitor(self):
        obs = ObsolescenceMonitorService.evaluate_obsolescence_risk(self.product)
        # Because DoC (400) > shelf life (365), hazard must be flagged
        self.assertEqual(obs["obsolescence_status"], "EXPIRATION_HAZARD")
        self.assertGreater(obs["capital_at_risk_usd"], 0)
        self.assertEqual(obs["recommended_action"], "PROMOTIONAL_MARKDOWN_OR_STOCK_TRANSFER")

        # Test endpoint
        res = self.client.get(reverse('analytics-obsolescence-risk'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("total_capital_at_risk_usd", res.data)

    def test_edi_850_generation(self):
        edi_text = EDIGeneratorService.generate_edi_850(self.po)
        self.assertIn("ISA*", edi_text)
        self.assertIn("ST*850*", edi_text)
        self.assertIn("PO1*", edi_text)
        self.assertIn(self.product.sku, edi_text)

        # Test endpoint
        res = self.client.get(f"/api/v1/purchase-orders/{self.po.id}/export-edi/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["erp_transaction_type"], "PURCHASE_ORDER_850")
        self.assertIn("ISA*", res.data["edi_850_document"])
