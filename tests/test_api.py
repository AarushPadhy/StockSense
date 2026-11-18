"""
Tests for Supply Chain REST API Endpoints.
"""

from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from inventory_core.models import Product, Supplier, InventoryLevel, PurchaseOrder


class APIEndpointTestCase(APITestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="Supplier Alpha",
            region="APAC",
            lead_time_days=10,
            risk_score=0.15
        )
        self.product = Product.objects.create(
            sku="SKU-API-001",
            name="High-Voltage Relay",
            category="Electromechanical",
            unit_cost=Decimal("12.50"),
            unit_price=Decimal("30.00"),
            baseline_rop=80,
            minimum_order_qty=25
        )
        self.inventory = InventoryLevel.objects.create(
            product=self.product,
            primary_supplier=self.supplier,
            current_stock=20,
            allocated_stock=5,
            safety_stock=15,
            days_of_stock_cover=Decimal("3.50"),
            stock_status=InventoryLevel.StockStatus.CRITICAL_STOCKOUT
        )

    def test_replenishment_dashboard_endpoint(self):
        url = reverse('replenishment-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("summary_kpis", response.data)
        self.assertIn("urgent_replenishment_queue", response.data)

    def test_trigger_replenishment_action_endpoint(self):
        url = reverse('trigger-draft-po')
        payload = {
            "product_sku": self.product.sku,
            "auto_draft_po": True,
            "async_execution": False
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertIn("purchase_order_drafted", response.data["data"])

        # Verify PO created in database
        po = PurchaseOrder.objects.filter(product=self.product).first()
        self.assertIsNotNone(po)
        self.assertEqual(po.status, PurchaseOrder.POStatus.PENDING_APPROVAL)

    def test_purchase_order_approve_action(self):
        po = PurchaseOrder.objects.create(
            po_number="PO-APPROVAL-001",
            supplier=self.supplier,
            product=self.product,
            quantity=50,
            unit_cost=Decimal("12.50"),
            status=PurchaseOrder.POStatus.PENDING_APPROVAL
        )
        url = f"/api/v1/purchase-orders/{po.id}/approve/"
        response = self.client.post(url, {"approved_by": "Supply Chain VP"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.POStatus.APPROVED)
        self.assertEqual(po.approved_by, "Supply Chain VP")
