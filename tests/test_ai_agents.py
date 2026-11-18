"""
Tests for Multi-Agent AI Orchestrator and Disruption Monitor.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from inventory_core.models import Product, Supplier, InventoryLevel, SalesHistory, PurchaseOrder, DisruptionAlert
from inventory_core.services.ai_agents import MultiAgentSupplyChainOrchestrator
from inventory_core.services.disruption_monitor import PredictiveDisruptionMonitor


class MultiAgentTestCase(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="Primary Fab APAC",
            region="APAC",
            lead_time_days=14,
            risk_score=0.20,
            reliability_rating=0.95
        )
        self.alt_supplier = Supplier.objects.create(
            name="Secondary Fab NA",
            region="NA",
            lead_time_days=7,
            risk_score=0.05,
            reliability_rating=0.99
        )
        self.product = Product.objects.create(
            sku="SKU-AI-001",
            name="AI Processing Unit",
            category="Semiconductors",
            unit_cost=Decimal("50.00"),
            unit_price=Decimal("150.00"),
            baseline_rop=100,
            minimum_order_qty=50
        )
        self.inventory = InventoryLevel.objects.create(
            product=self.product,
            primary_supplier=self.supplier,
            current_stock=15,  # Deliberately low stock to trigger Critical Stockout
            allocated_stock=5,
            safety_stock=20
        )
        # Create some sales history
        for i in range(15):
            SalesHistory.objects.create(
                product=self.product,
                recorded_at=timezone.now() - timezone.timedelta(days=i),
                quantity_sold=5,
                unit_selling_price=Decimal("150.00")
            )

    def test_multi_agent_pipeline_execution(self):
        orchestrator = MultiAgentSupplyChainOrchestrator()
        result = orchestrator.run_replenishment_pipeline(product_sku=self.product.sku, auto_draft_po=True)

        self.assertIn("demand_forecast", result)
        self.assertIn("inventory_health", result)
        self.assertIn("procurement_plan", result)

        inv_health = result["inventory_health"]
        self.assertIn("days_of_stock_cover", inv_health)
        self.assertEqual(inv_health["stock_status"], InventoryLevel.StockStatus.CRITICAL_STOCKOUT)

        plan = result["procurement_plan"]
        self.assertIn(plan["action"], ["EXPEDITE_PO", "DRAFT_PO"])
        self.assertGreater(plan["recommended_order_quantity"], 0)
        self.assertIn("=== MULTI-AGENT PROCUREMENT REASONING ===", plan["ai_chain_of_thought"])

        # Check PO was drafted
        po = PurchaseOrder.objects.filter(product=self.product).first()
        self.assertIsNotNone(po)
        self.assertEqual(po.status, PurchaseOrder.POStatus.PENDING_APPROVAL)
        self.assertIn("MULTI-AGENT", po.ai_reasoning)

    def test_disruption_monitor_and_supplier_failover(self):
        # Trigger predictive disruption scan
        alerts = PredictiveDisruptionMonitor.fetch_and_analyze_news()
        self.assertGreater(len(alerts), 0)

        # Re-run replenishment with disruption active
        orchestrator = MultiAgentSupplyChainOrchestrator()
        result = orchestrator.run_replenishment_pipeline(product_sku=self.product.sku, auto_draft_po=False)

        plan = result["procurement_plan"]
        self.assertTrue(plan["recommended_order_quantity"] > 0)
