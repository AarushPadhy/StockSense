"""
Domain-Driven Database Architecture for Supply Chain & Inventory Optimization.

Design Principles:
1. Thin models with domain encapsulation, constraints, and indexes.
2. TimescaleDB ready: SalesHistory is structured for hypertable time-partitioning on recorded_at.
3. pgvector compatible: DisruptionAlert provides vector embedding capabilities for semantic search / RAG.
4. Business logic is strictly delegated to services/ layer.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


# ==============================================================================
# Domain Model: Product (Core Entity)
# ==============================================================================
class Product(models.Model):
    """
    Aggregate root representing an item in the supply catalog.
    Maintains baseline Reorder Point (ROP) for comparison against AI dynamic ROP.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique Stock Keeping Unit code"
    )
    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True, default='')

    # Unit financial economics
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Static baseline metrics (traditional legacy values)
    baseline_rop = models.PositiveIntegerField(
        default=100,
        help_text="Legacy static Reorder Point (baseline to compare dynamic AI ROP against)"
    )
    minimum_order_qty = models.PositiveIntegerField(
        default=10,
        help_text="Supplier minimum order quantity (MOQ)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['sku']

    def __str__(self):
        return f"{self.sku} - {self.name}"


# ==============================================================================
# Domain Model: Supplier (Entity)
# ==============================================================================
class Supplier(models.Model):
    """
    Represents an external vendor / manufacturer in the supply network.
    Tracks empirical lead times and dynamic risk scores for resilient planning.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    contact_email = models.EmailField(blank=True)
    region = models.CharField(max_length=100, blank=True, help_text="Geographical origin (e.g. APAC, EMEA, NA)")

    # Operational metrics
    lead_time_days = models.PositiveIntegerField(
        default=14,
        help_text="Average lead time in calendar days"
    )
    risk_score = models.FloatField(
        default=0.10,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        db_index=True,
        help_text="Composite risk index from 0.0 (low risk) to 1.0 (critical risk)"
    )
    reliability_rating = models.FloatField(
        default=0.95,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Historical fulfillment accuracy (0.0 to 1.0)"
    )
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Risk: {self.risk_score:.2f}, LT: {self.lead_time_days}d)"


# ==============================================================================
# Domain Model: InventoryLevel (Aggregate Component)
# ==============================================================================
class InventoryLevel(models.Model):
    """
    Real-time stock state for a product.
    Tracks on-hand inventory and dynamically updated Days of Stock Cover (DoC).
    """
    class StockStatus(models.TextChoices):
        OPTIMAL = 'OPTIMAL', 'Optimal'
        WARNING_LOW = 'WARNING_LOW', 'Warning: Low Stock'
        CRITICAL_STOCKOUT = 'CRITICAL_STOCKOUT', 'Critical: Stockout Imminent'
        OVERSTOCKED = 'OVERSTOCKED', 'Overstocked'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory_level',
        db_index=True
    )
    primary_supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplied_inventories'
    )

    current_stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Physical units available on hand"
    )
    allocated_stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Stock reserved for open outbound sales orders"
    )
    safety_stock = models.IntegerField(
        default=20,
        validators=[MinValueValidator(0)],
        help_text="Buffer stock calculated to absorb demand spikes"
    )

    # Dynamic metrics calculated by Inventory Agent
    days_of_stock_cover = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        db_index=True,
        help_text="Dynamic Days of Cover: current_stock / forecasted daily demand"
    )
    dynamic_rop = models.IntegerField(
        default=100,
        help_text="AI-recalculated Reorder Point factoring demand & lead times"
    )
    stock_status = models.CharField(
        max_length=30,
        choices=StockStatus.choices,
        default=StockStatus.OPTIMAL,
        db_index=True
    )

    last_replenished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory Level"
        verbose_name_plural = "Inventory Levels"
        indexes = [
            models.Index(fields=['product', 'stock_status']),
            models.Index(fields=['days_of_stock_cover']),
        ]

    @property
    def available_stock(self) -> int:
        """Net stock available for fulfillment."""
        return max(0, self.current_stock - self.allocated_stock)

    def __str__(self):
        return f"{self.product.sku} - Stock: {self.current_stock} (DoC: {self.days_of_stock_cover}d)"


# ==============================================================================
# Domain Model: SalesHistory (Time-Series / TimescaleDB Hypertable)
# ==============================================================================
class SalesHistory(models.Model):
    """
    Time-series sales transactional log.
    Architected for TimescaleDB hypertable conversion:
      SELECT create_hypertable('inventory_core_saleshistory', 'recorded_at');
    """
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='sales_history'
    )
    recorded_at = models.DateTimeField(
        db_index=True,
        help_text="Exact timestamp of transaction/daily aggregate (Timescale partition key)"
    )
    quantity_sold = models.PositiveIntegerField(
        default=1,
        help_text="Number of units sold"
    )
    unit_selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    sales_channel = models.CharField(
        max_length=64,
        default='ONLINE_DIRECT',
        db_index=True
    )

    class Meta:
        verbose_name = "Sales History Record"
        verbose_name_plural = "Sales History Records"
        indexes = [
            models.Index(fields=['recorded_at', 'product']),
            models.Index(fields=['product', 'recorded_at']),
        ]
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.product.sku} on {self.recorded_at.strftime('%Y-%m-%d')}: {self.quantity_sold} units"


# ==============================================================================
# Domain Model: PurchaseOrder (Procurement Entity)
# ==============================================================================
class PurchaseOrder(models.Model):
    """
    Autonomous or manual procurement order drafted based on AI recommendations.
    Maintains complete audit trail and AI reasoning.
    """
    class POStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        TRANSMITTED = 'TRANSMITTED', 'Transmitted to Supplier'
        FULFILLED = 'FULFILLED', 'Fulfilled'

    class TriggerSource(models.TextChoices):
        AI_AGENT = 'AI_AGENT', 'AI Autonomous Planning Agent'
        MANUAL = 'MANUAL', 'Manual Human Intervention'
        SCHEDULED_BATCH = 'SCHEDULED_BATCH', 'Scheduled Batch Routine'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    po_number = models.CharField(max_length=64, unique=True, db_index=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity ordered"
    )
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00')
    )
    status = models.CharField(
        max_length=30,
        choices=POStatus.choices,
        default=POStatus.PENDING_APPROVAL,
        db_index=True
    )
    trigger_source = models.CharField(
        max_length=30,
        choices=TriggerSource.choices,
        default=TriggerSource.AI_AGENT
    )

    # Multi-Agent Chain-of-Thought Explainability
    ai_reasoning = models.TextField(
        blank=True,
        help_text="Full Chain-of-Thought reasoning output from the Planning Agent"
    )
    risk_assessment_summary = models.TextField(
        blank=True,
        help_text="Supplier & lead-time risk evaluation at time of drafting"
    )

    approved_by = models.CharField(max_length=150, blank=True, null=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.total_cost and self.unit_cost and self.quantity:
            self.total_cost = self.unit_cost * Decimal(self.quantity)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PO {self.po_number} ({self.status}) - {self.product.sku} x {self.quantity}"


# ==============================================================================
# Domain Model: DisruptionAlert (RAG & Intelligence Entity)
# ==============================================================================
class DisruptionAlert(models.Model):
    """
    External market, geopolitical, or logistical disruption flagged by RAG monitor.
    Stores semantic vector embedding representation for pgvector similarity lookups.
    """
    class Severity(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    headline = models.CharField(max_length=512, db_index=True)
    source_url = models.URLField(blank=True, default='')
    source_name = models.CharField(max_length=128, default='Global News Feed')
    
    # Relationships
    affected_supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disruption_alerts'
    )
    affected_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disruption_alerts'
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        db_index=True
    )
    estimated_delay_days = models.PositiveIntegerField(
        default=0,
        help_text="Projected delay addition to supplier baseline lead time"
    )
    impact_analysis = models.TextField(
        help_text="AI RAG synthesis explaining direct supply chain risk"
    )
    
    # Semantic embedding vector (1536-dim standard, compatible with pgvector)
    # Stored as JSONField for portable cross-database execution (PostgreSQL / SQLite)
    embedding_vector = models.JSONField(
        null=True,
        blank=True,
        help_text="Vector embedding representation (1536d) for pgvector cosine search"
    )

    is_resolved = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Disruption Alert"
        verbose_name_plural = "Disruption Alerts"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['severity', 'is_resolved']),
            models.Index(fields=['affected_supplier', 'is_resolved']),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.headline[:60]} (+{self.estimated_delay_days}d delay)"


# ==============================================================================
# Domain Model: Warehouse (Multi-Echelon Network Entity)
# ==============================================================================
class Warehouse(models.Model):
    """
    Physical distribution hub or fulfillment center in a multi-echelon supply network.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True, db_index=True, help_text="e.g. WH-EAST-01")
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, help_text="City / State")
    region = models.CharField(max_length=64, default="NA")
    capacity_units = models.PositiveIntegerField(default=100000)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.region})"


class WarehouseInventory(models.Model):
    """
    Product stock allocated at a specific physical warehouse node.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_positions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='warehouse_positions')
    current_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    allocated_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Warehouse Inventory Position"
        verbose_name_plural = "Warehouse Inventory Positions"
        unique_together = ('warehouse', 'product')
        indexes = [
            models.Index(fields=['warehouse', 'product']),
        ]

    @property
    def available_stock(self) -> int:
        return max(0, self.current_stock - self.allocated_stock)

    def __str__(self):
        return f"{self.warehouse.code} | {self.product.sku}: {self.current_stock} units"


class StockTransferRecommendation(models.Model):
    """
    Intra-network stock transfer recommended by Planning Agent to avert stockouts
    faster and cheaper than external supplier purchase orders.
    """
    class TransferStatus(models.TextChoices):
        RECOMMENDED = 'RECOMMENDED', 'Recommended'
        APPROVED = 'APPROVED', 'Approved'
        IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_transfers')
    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='outbound_transfers')
    target_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inbound_transfers')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    estimated_transit_days = models.PositiveIntegerField(default=3)
    cost_savings_usd = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    ai_reasoning = models.TextField(help_text="Agent rationale comparing internal transfer vs external PO")
    status = models.CharField(max_length=30, choices=TransferStatus.choices, default=TransferStatus.RECOMMENDED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock Transfer Recommendation"
        verbose_name_plural = "Stock Transfer Recommendations"
        ordering = ['-created_at']

    def __str__(self):
        return f"Transfer {self.quantity}x {self.product.sku}: {self.source_warehouse.code} -> {self.target_warehouse.code} ({self.status})"


# ==============================================================================
# Domain Model: Autonomous Auto-Pilot Policy & Execution Log
# ==============================================================================
class AutoPilotPolicy(models.Model):
    """
    Configuration and guardrails for fully autonomous supply chain operations.
    When enabled, the AI moves beyond passive recommendations to active execution:
    auto-approving POs within budget limits, generating EDI 850, and dispatching
    inter-warehouse stock transfers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, default="Primary Autonomous Policy")
    is_enabled = models.BooleanField(
        default=True,
        help_text="Master switch: if true, autonomous auto-pilot actively executes orders & transfers"
    )
    max_auto_po_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('15000.00'),
        help_text="Maximum financial threshold for autonomous zero-touch PO approval. Orders exceeding this are held for human sign-off."
    )
    min_supplier_reliability = models.FloatField(
        default=0.80,
        help_text="Minimum vendor reliability rating required for autonomous PO transmission."
    )
    auto_execute_transfers = models.BooleanField(
        default=True,
        help_text="Automatically dispatch inter-warehouse transfers when inventory imbalances are detected."
    )
    auto_transmit_edi = models.BooleanField(
        default=True,
        help_text="Automatically generate and transmit ANSI X12 EDI 850 payloads to vendors upon PO approval."
    )
    auto_failover_on_disruption = models.BooleanField(
        default=True,
        help_text="Automatically divert orders to secondary domestic suppliers if active disruption threatens primary supplier."
    )
    total_automated_actions = models.PositiveIntegerField(default=0)
    total_automated_spend_usd = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal('0.00')
    )
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Autonomous Auto-Pilot Policy"
        verbose_name_plural = "Autonomous Auto-Pilot Policies"

    @classmethod
    def get_active_policy(cls) -> "AutoPilotPolicy":
        policy = cls.objects.first()
        if not policy:
            policy = cls.objects.create(
                is_enabled=True,
                max_auto_po_value=Decimal('15000.00'),
                min_supplier_reliability=0.80,
                auto_execute_transfers=True,
                auto_transmit_edi=True,
                auto_failover_on_disruption=True
            )
        return policy

    def __str__(self):
        status = "ACTIVE" if self.is_enabled else "PAUSED"
        return f"Auto-Pilot [{status}] Max PO: ${self.max_auto_po_value:,.2f}"


class AutonomousActionLog(models.Model):
    """
    Immutable audit trail recording every autonomous action executed by the platform.
    Provides complete transparency for business owners and CFOs.
    """
    class ActionType(models.TextChoices):
        PO_TRANSMITTED = 'PO_TRANSMITTED', 'Autonomous Purchase Order Transmitted'
        TRANSFER_DISPATCHED = 'TRANSFER_DISPATCHED', 'Autonomous Warehouse Transfer Dispatched'
        SUPPLIER_FAILOVER = 'SUPPLIER_FAILOVER', 'Autonomous Disruption Vendor Failover'
        GUARDRAIL_HELD = 'GUARDRAIL_HELD', 'Held for Human Sign-off (Guardrail Threshold)'
        INVENTORY_REBALANCED = 'INVENTORY_REBALANCED', 'Dynamic Reorder Point Adjusted'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_type = models.CharField(max_length=40, choices=ActionType.choices, db_index=True)
    reference_code = models.CharField(max_length=100, db_index=True, help_text="e.g. PO number or Transfer ID")
    product_sku = models.CharField(max_length=64, db_index=True)
    headline = models.CharField(max_length=255)
    details = models.TextField()
    financial_impact_usd = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00')
    )
    edi_payload = models.TextField(blank=True, default='')
    status = models.CharField(max_length=30, default="COMPLETED", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Autonomous Action Log"
        verbose_name_plural = "Autonomous Action Logs"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at.strftime('%H:%M:%S')}] {self.action_type}: {self.headline}"


