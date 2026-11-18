from django.test import TestCase, Client
from django.urls import reverse
from inventory_core.models import Product, Supplier, InventoryLevel
from inventory_core.services.ai_negotiator import AIVolumeDiscountArbitrageur
from inventory_core.services.revenue_risk import RevenueRiskEngine
from inventory_core.services.copilot import StockSenseCopilot
import json


class UniqueAIFeaturesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.supplier = Supplier.objects.create(
            name="Shenzhen Precision Dynamics",
            contact_email="supply@sz-precision.com",
            lead_time_days=14,
            risk_score=0.18,
            region="APAC"
        )
        self.product = Product.objects.create(
            sku="SKU-TEST-AI-01",
            name="Quantum Precision Drone Sensor",
            category="Sensors",
            unit_cost=50.00,
            unit_price=120.00,
            minimum_order_qty=10
        )
        self.inventory = InventoryLevel.objects.create(
            product=self.product,
            current_stock=25,
            allocated_stock=5,
            dynamic_rop=40,
            safety_stock=15,
            days_of_stock_cover=3.5,
            stock_status=InventoryLevel.StockStatus.CRITICAL_STOCKOUT,
            primary_supplier=self.supplier
        )

    def test_volume_discount_arbitrageur(self):
        result = AIVolumeDiscountArbitrageur.analyze_discount_arbitrage(
            product_sku=self.product.sku,
            planned_order_qty=100
        )
        self.assertEqual(result["sku"], self.product.sku)
        self.assertEqual(len(result["tiers"]), 3)
        self.assertIn("negotiation_email_body", result)
        self.assertIn("Shenzhen Precision Dynamics", result["negotiation_email_body"])

    def test_revenue_risk_engine(self):
        data = RevenueRiskEngine.evaluate_catalog_financial_exposure()
        self.assertIn("summary", data)
        self.assertIn("vulnerable_products", data)
        self.assertGreaterEqual(data["summary"]["vulnerable_skus_count"], 1)
        self.assertGreater(data["summary"]["total_revenue_at_risk_usd"], 0)

    def test_copilot_service(self):
        ans1 = StockSenseCopilot.ask("Which products will run out of stock soon?")
        self.assertIn("answer", ans1)
        self.assertEqual(ans1["intent"], "STOCKOUT_HAZARDS")

        ans2 = StockSenseCopilot.ask("How much money do we need for purchase orders?")
        self.assertEqual(ans2["intent"], "FINANCIAL_CAPITAL_INQUIRY")

        ans3 = StockSenseCopilot.ask("Which supplier is the most delayed or risky?")
        self.assertEqual(ans3["intent"], "SUPPLIER_PERFORMANCE")

    def test_api_endpoints(self):
        # 1. Copilot API
        r1 = self.client.post(
            "/api/v1/ai/copilot/",
            data=json.dumps({"query": "What are my biggest stockout risks?"}),
            content_type="application/json"
        )
        self.assertEqual(r1.status_code, 200)
        self.assertIn("answer", r1.json())

        # 2. Revenue Risk Shield API
        r2 = self.client.get("/api/v1/ai/revenue-at-risk/")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("total_revenue_at_risk_usd", r2.json()["summary"])

        # 3. AI Volume Negotiator API
        r3 = self.client.post(
            "/api/v1/ai/negotiate/",
            data=json.dumps({"product_sku": self.product.sku, "planned_order_qty": 80}),
            content_type="application/json"
        )
        self.assertEqual(r3.status_code, 200)
        self.assertIn("negotiation_email_body", r3.json())
