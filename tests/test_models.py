"""
Unit tests for Inventory Core Domain Models.
"""

from decimal import Decimal
from django.test import TestCase
from inventory_core.models import Product, Supplier, InventoryLevel, PurchaseOrder, DisruptionAlert


class ModelTestCase(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="Shenzhen Components",
            lead_time_days=14,
            risk_score=0.20,
            reliability_rating=0.95
        )
        self.product = Product.objects.create(
            sku="SKU-TEST-001",
            name="MCU Controller",
            category="Semiconductors",
            unit_cost=Decimal("5.00"),
            unit_price=Decimal("15.00"),
            baseline_rop=100,
            minimum_order_qty=20
        )

    def test_product_creation(self):
        self.assertEqual(self.product.sku, "SKU-TEST-001")
        self.assertEqual(str(self.product), "SKU-TEST-001 - MCU Controller")

    def test_inventory_level_properties(self):
        inv = InventoryLevel.objects.create(
            product=self.product,
            primary_supplier=self.supplier,
            current_stock=150,
            allocated_stock=30,
            safety_stock=25
        )
        self.assertEqual(inv.available_stock, 120)

    def test_purchase_order_cost_calculation(self):
        po = PurchaseOrder.objects.create(
            po_number="PO-TEST-001",
            supplier=self.supplier,
            product=self.product,
            quantity=100,
            unit_cost=Decimal("5.00")
        )
        self.assertEqual(po.total_cost, Decimal("500.00"))
        self.assertEqual(po.status, PurchaseOrder.POStatus.PENDING_APPROVAL)
