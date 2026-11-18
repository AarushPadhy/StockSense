"""
Django Admin Registration for Inventory Core.
"""

from django.contrib import admin
from inventory_core.models import (
    Product,
    Supplier,
    InventoryLevel,
    SalesHistory,
    PurchaseOrder,
    DisruptionAlert,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'unit_cost', 'unit_price', 'baseline_rop', 'minimum_order_qty')
    search_fields = ('sku', 'name', 'category')
    list_filter = ('category',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'lead_time_days', 'risk_score', 'reliability_rating', 'is_active')
    search_fields = ('name', 'region')
    list_filter = ('region', 'is_active')


@admin.register(InventoryLevel)
class InventoryLevelAdmin(admin.ModelAdmin):
    list_display = ('product', 'current_stock', 'allocated_stock', 'days_of_stock_cover', 'dynamic_rop', 'stock_status')
    search_fields = ('product__sku', 'product__name')
    list_filter = ('stock_status',)


@admin.register(SalesHistory)
class SalesHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'recorded_at', 'quantity_sold', 'unit_selling_price', 'sales_channel')
    search_fields = ('product__sku',)
    list_filter = ('sales_channel', 'recorded_at')


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'product', 'quantity', 'total_cost', 'status', 'trigger_source', 'created_at')
    search_fields = ('po_number', 'product__sku', 'supplier__name')
    list_filter = ('status', 'trigger_source', 'created_at')
    readonly_fields = ('ai_reasoning', 'risk_assessment_summary')


@admin.register(DisruptionAlert)
class DisruptionAlertAdmin(admin.ModelAdmin):
    list_display = ('headline', 'affected_supplier', 'severity', 'estimated_delay_days', 'is_resolved', 'created_at')
    search_fields = ('headline', 'affected_supplier__name')
    list_filter = ('severity', 'is_resolved')
