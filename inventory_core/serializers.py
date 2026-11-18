"""
Django REST Framework Serializers for Supply Chain & Inventory Optimization Platform.
"""

from rest_framework import serializers
from inventory_core.models import (
    Product,
    Supplier,
    InventoryLevel,
    SalesHistory,
    PurchaseOrder,
    DisruptionAlert,
    Warehouse,
    WarehouseInventory,
    StockTransferRecommendation,
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_email', 'region',
            'lead_time_days', 'risk_score', 'reliability_rating',
            'is_active', 'created_at', 'updated_at'
        ]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'name', 'category', 'description',
            'unit_cost', 'unit_price', 'baseline_rop', 'minimum_order_qty',
            'created_at', 'updated_at'
        ]


class InventoryLevelSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_sku = serializers.CharField(write_only=True, required=False)
    primary_supplier = SupplierSerializer(read_only=True)
    available_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryLevel
        fields = [
            'id', 'product', 'product_sku', 'primary_supplier',
            'current_stock', 'allocated_stock', 'available_stock',
            'safety_stock', 'days_of_stock_cover', 'dynamic_rop',
            'stock_status', 'last_replenished_at', 'updated_at'
        ]


class SalesHistorySerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = SalesHistory
        fields = [
            'id', 'product', 'product_sku', 'recorded_at',
            'quantity_sold', 'unit_selling_price', 'sales_channel'
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name',
            'product', 'product_sku', 'product_name',
            'quantity', 'unit_cost', 'total_cost',
            'status', 'trigger_source', 'ai_reasoning',
            'risk_assessment_summary', 'approved_by', 'approved_at',
            'expected_delivery_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['po_number', 'created_at', 'updated_at']


class DisruptionAlertSerializer(serializers.ModelSerializer):
    affected_supplier_name = serializers.CharField(source='affected_supplier.name', read_only=True)
    affected_product_sku = serializers.CharField(source='affected_product.sku', read_only=True)

    class Meta:
        model = DisruptionAlert
        fields = [
            'id', 'headline', 'source_name', 'source_url',
            'affected_supplier', 'affected_supplier_name',
            'affected_product', 'affected_product_sku',
            'severity', 'estimated_delay_days', 'impact_analysis',
            'is_resolved', 'published_at', 'created_at'
        ]


# Request / Action Serializers
class ReplenishmentTriggerSerializer(serializers.Serializer):
    product_sku = serializers.CharField(required=True)
    auto_draft_po = serializers.BooleanField(default=True)
    async_execution = serializers.BooleanField(default=False)


class CSVUploadSerializer(serializers.Serializer):
    file_type = serializers.ChoiceField(
        choices=['suppliers', 'products', 'inventory', 'sales']
    )
    file = serializers.FileField(required=True)
    async_processing = serializers.BooleanField(default=False)


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'code', 'name', 'location', 'region', 'capacity_units', 'is_active', 'created_at']


class WarehouseInventorySerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = WarehouseInventory
        fields = ['id', 'warehouse', 'warehouse_code', 'product', 'product_sku', 'current_stock', 'allocated_stock', 'available_stock', 'updated_at']


class StockTransferRecommendationSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    source_warehouse_code = serializers.CharField(source='source_warehouse.code', read_only=True)
    target_warehouse_code = serializers.CharField(source='target_warehouse.code', read_only=True)

    class Meta:
        model = StockTransferRecommendation
        fields = [
            'id', 'product', 'product_sku', 'source_warehouse', 'source_warehouse_code',
            'target_warehouse', 'target_warehouse_code', 'quantity', 'estimated_transit_days',
            'cost_savings_usd', 'ai_reasoning', 'status', 'created_at', 'updated_at'
        ]


class SimulationRequestSerializer(serializers.Serializer):
    product_sku = serializers.CharField(required=True)
    demand_surge_percent = serializers.FloatField(default=0.0, min_value=-90.0, max_value=500.0)
    lead_time_delay_days = serializers.IntegerField(default=0, min_value=0, max_value=180)
    supplier_risk_spike = serializers.FloatField(default=0.0, min_value=-1.0, max_value=1.0)
    target_service_level = serializers.FloatField(default=0.95, min_value=0.50, max_value=0.999)


class SemanticSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=True, min_length=2, max_length=500)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=20)

