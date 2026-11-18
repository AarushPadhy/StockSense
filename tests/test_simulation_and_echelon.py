"""
Tests for What-If Simulation, King-Formula Safety Stock, and Multi-Echelon Rebalancing.
"""

from decimal import Decimal
from django.test import TestCase
from inventory_core.models import Product, Supplier, InventoryLevel, Warehouse, WarehouseInventory, StockTransferRecommendation
from inventory_core.services.simulation import SupplyChainSimulator
from inventory_core.services.multi_echelon import MultiEchelonService
from inventory_core.services.disruption_monitor import PredictiveDisruptionMonitor


class AdvancedFeaturesTestCase(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="Apex Precision Components",
            lead_time_days=14,
            risk_score=0.15
        )
        self.product = Product.objects.create(
            sku="SKU-SIM-001",
            name="Solid State Relay 40A",
            category="Power Electronics",
            unit_cost=Decimal("18.00"),
            unit_price=Decimal("42.00"),
            baseline_rop=120,
            minimum_order_qty=30
        )
        self.inventory = InventoryLevel.objects.create(
            product=self.product,
            primary_supplier=self.supplier,
            current_stock=100,
            allocated_stock=10,
            safety_stock=25
        )

    def test_what_if_simulation_engine(self):
        # Run what-if scenario with +40% surge and +10 days shipping delay
        result = SupplyChainSimulator.run_what_if_scenario(
            product_sku=self.product.sku,
            demand_surge_percent=40.0,
            lead_time_delay_days=10,
            supplier_risk_spike=0.25,
            target_service_level=0.98
        )

        self.assertEqual(result["sku"], self.product.sku)
        self.assertIn("baseline_metrics", result)
        self.assertIn("stressed_metrics", result)
        self.assertIn("hedging_recommendation", result)

        base = result["baseline_metrics"]
        stress = result["stressed_metrics"]

        # Daily demand under surge should be higher than baseline
        self.assertGreater(stress["daily_demand"], base["daily_demand"])
        # Days of cover under surge should be lower than baseline
        self.assertLess(stress["days_of_stock_cover"], base["days_of_stock_cover"])
        # Optimal safety stock should increase
        self.assertGreater(stress["optimal_safety_stock"], 0)
        self.assertIn("WHAT-IF SCENARIO STRESS TEST", result["ai_chain_of_thought"])

    def test_multi_echelon_internal_transfer(self):
        transfer = MultiEchelonService.evaluate_inter_warehouse_transfer(
            product_sku=self.product.sku,
            required_units=40
        )
        self.assertIsNotNone(transfer)
        self.assertEqual(transfer["sku"], self.product.sku)
        self.assertGreater(transfer["quantity"], 0)
        self.assertEqual(transfer["transit_days"], 3)
        self.assertGreater(transfer["cost_savings_usd"], 0)

        # Check DB record
        rec = StockTransferRecommendation.objects.filter(product=self.product).first()
        self.assertIsNotNone(rec)
        self.assertEqual(rec.status, StockTransferRecommendation.TransferStatus.RECOMMENDED)

    def test_semantic_search_disruptions(self):
        # Fetch news first
        PredictiveDisruptionMonitor.fetch_and_analyze_news()

        # Semantic query
        results = PredictiveDisruptionMonitor.semantic_search_disruptions(query="port terminals strike", top_k=2)
        self.assertGreater(len(results), 0)
        self.assertIn("similarity_score", results[0])
