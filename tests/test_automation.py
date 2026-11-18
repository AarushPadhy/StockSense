"""
Automated Unit and Integration Tests for Autonomous Auto-Pilot Execution Engine.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from inventory_core.models import (
    Product,
    Supplier,
    InventoryLevel,
    PurchaseOrder,
    Warehouse,
    WarehouseInventory,
    StockTransferRecommendation,
    AutoPilotPolicy,
    AutonomousActionLog,
)
from inventory_core.services.automation_engine import AutonomousExecutionEngine


class AutonomousExecutionEngineTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Seed supplier & product
        self.supplier = Supplier.objects.create(
            name="Apex Precision Test",
            lead_time_days=10,
            risk_score=0.15,
            reliability_rating=0.95
        )
        self.product = Product.objects.create(
            sku="SKU-AUTO-001",
            name="Autonomous LiDAR Sensor",
            category="Sensors",
            unit_cost=Decimal('50.00'),
            unit_price=Decimal('120.00'),
            baseline_rop=80
        )
        self.inv = InventoryLevel.objects.create(
            product=self.product,
            current_stock=10,
            safety_stock=25,
            days_of_stock_cover=Decimal('1.5'),
            primary_supplier=self.supplier,
            stock_status=InventoryLevel.StockStatus.CRITICAL_STOCKOUT
        )

        # Warehouses for transfer test
        self.wh_source = Warehouse.objects.create(code="WH-TEST-EAST", name="East Hub", location="Newark")
        self.wh_target = Warehouse.objects.create(code="WH-TEST-WEST", name="West Hub", location="Reno")
        self.wh_inv_source = WarehouseInventory.objects.create(
            warehouse=self.wh_source,
            product=self.product,
            current_stock=200
        )

        self.transfer = StockTransferRecommendation.objects.create(
            product=self.product,
            source_warehouse=self.wh_source,
            target_warehouse=self.wh_target,
            quantity=50,
            estimated_transit_days=2,
            cost_savings_usd=Decimal('420.00'),
            ai_reasoning="Test transfer recommendation",
            status=StockTransferRecommendation.TransferStatus.RECOMMENDED
        )

        self.po = PurchaseOrder.objects.create(
            po_number="PO-TEST-AUTO-999",
            supplier=self.supplier,
            product=self.product,
            quantity=100,
            unit_cost=Decimal('50.00'),
            total_cost=Decimal('5000.00'),
            status=PurchaseOrder.POStatus.PENDING_APPROVAL,
            ai_reasoning="Test PO awaiting execution"
        )

    def test_autopilot_policy_defaults(self):
        policy = AutoPilotPolicy.get_active_policy()
        self.assertTrue(policy.is_enabled)
        self.assertEqual(policy.max_auto_po_value, Decimal('15000.00'))
        self.assertEqual(policy.min_supplier_reliability, 0.80)

    def test_single_po_transmission(self):
        res = AutonomousExecutionEngine.transmit_purchase_order_by_id(str(self.po.id))
        self.assertEqual(res["status"], "SUCCESS")
        
        self.po.refresh_from_db()
        self.assertEqual(self.po.status, PurchaseOrder.POStatus.TRANSMITTED)
        self.assertEqual(self.po.approved_by, "OPERATOR_OVERRIDE")

        # Verify audit log created
        log = AutonomousActionLog.objects.filter(reference_code=self.po.po_number).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action_type, AutonomousActionLog.ActionType.PO_TRANSMITTED)
        self.assertTrue("ISA*00*" in log.edi_payload)

    def test_single_stock_transfer_dispatch(self):
        initial_stock = self.wh_inv_source.current_stock
        res = AutonomousExecutionEngine.execute_stock_transfer_by_id(str(self.transfer.id))
        self.assertEqual(res["status"], "SUCCESS")

        self.transfer.refresh_from_db()
        self.assertEqual(self.transfer.status, StockTransferRecommendation.TransferStatus.IN_TRANSIT)

        self.wh_inv_source.refresh_from_db()
        self.assertEqual(self.wh_inv_source.current_stock, initial_stock - self.transfer.quantity)

    def test_run_autonomous_cycle(self):
        res = AutonomousExecutionEngine.run_autonomous_cycle(force=True)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertGreaterEqual(res["total_actions_executed"], 1)

    def test_automation_api_endpoints(self):
        # 1. Get status
        resp = self.client.get('/api/v1/automation/status/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn("is_enabled", resp.data)

        # 2. Toggle / update policy
        resp = self.client.post('/api/v1/automation/toggle/', {
            "is_enabled": True,
            "max_auto_po_value": 20000.0
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["policy"]["max_auto_po_value_usd"], 20000.0)

        # 3. Run cycle endpoint
        resp = self.client.post('/api/v1/automation/run-cycle/', {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "COMPLETED")

        # 4. Audit logs endpoint
        resp = self.client.get('/api/v1/automation/audit-logs/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn("logs", resp.data)

    def test_tts_ttr_alias_and_eoq_defaults(self):
        # Resilience alias
        resp = self.client.get('/api/v1/analytics/tts-ttr/')
        self.assertEqual(resp.status_code, 200)

        # EOQ without query param
        resp = self.client.get('/api/v1/analytics/eoq/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn("eoq_analysis", resp.data)
