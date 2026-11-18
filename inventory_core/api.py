"""
API Controllers and ViewSets for Supply Chain Optimization Platform.

Architectural Rule:
Views remain thin: request validation, delegating to the services/ layer,
and returning structured RESTful responses.
"""

import io
import logging
from decimal import Decimal
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

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
from inventory_core.serializers import (
    ProductSerializer,
    SupplierSerializer,
    InventoryLevelSerializer,
    SalesHistorySerializer,
    PurchaseOrderSerializer,
    DisruptionAlertSerializer,
    ReplenishmentTriggerSerializer,
    CSVUploadSerializer,
    WarehouseSerializer,
    WarehouseInventorySerializer,
    StockTransferRecommendationSerializer,
    SimulationRequestSerializer,
    SemanticSearchRequestSerializer,
)
from inventory_core.services.ingestion import PolarsDataIngestionService
from inventory_core.services.ai_agents import MultiAgentSupplyChainOrchestrator
from inventory_core.services.disruption_monitor import PredictiveDisruptionMonitor
from inventory_core.services.simulation import SupplyChainSimulator
from inventory_core.services.multi_echelon import MultiEchelonService
from inventory_core.services.analytics import SupplyChainAnalyticsService
from inventory_core.services.supplier_scorecard import SupplierScorecardService
from inventory_core.services.landed_cost import LandedCostService
from inventory_core.services.bullwhip import BullwhipSuppressionService
from inventory_core.services.obsolescence import ObsolescenceMonitorService
from inventory_core.services.edi_generator import EDIGeneratorService
from inventory_core.services.automation_engine import AutonomousExecutionEngine
from inventory_core.tasks import (
    task_run_replenishment_pipeline,
    task_ingest_csv_data,
    task_monitor_supplier_disruptions,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Real-time Replenishment Dashboard View
# ==============================================================================
class ReplenishmentDashboardView(APIView):
    """
    Exposes high-level telemetry and actionable operational KPIs:
    - Real-time stock cover breakdown (Critical, Warning, Optimal, Overstocked)
    - Active global disruption impact summary
    - Immediate action items for procurement officers
    """

    def get(self, request, *args, **kwargs):
        # Inventory health aggregations
        total_skus = InventoryLevel.objects.count()
        critical_count = InventoryLevel.objects.filter(
            stock_status=InventoryLevel.StockStatus.CRITICAL_STOCKOUT
        ).count()
        warning_count = InventoryLevel.objects.filter(
            stock_status=InventoryLevel.StockStatus.WARNING_LOW
        ).count()
        optimal_count = InventoryLevel.objects.filter(
            stock_status=InventoryLevel.StockStatus.OPTIMAL
        ).count()
        overstock_count = InventoryLevel.objects.filter(
            stock_status=InventoryLevel.StockStatus.OVERSTOCKED
        ).count()

        avg_cover = InventoryLevel.objects.aggregate(avg=Avg('days_of_stock_cover'))['avg'] or 0.0

        # Purchase order procurement pipeline
        pending_pos = PurchaseOrder.objects.filter(status=PurchaseOrder.POStatus.PENDING_APPROVAL)
        pending_po_count = pending_pos.count()
        pending_po_value = pending_pos.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

        # Active disruptions
        active_disruptions = DisruptionAlert.objects.filter(is_resolved=False)
        disruption_count = active_disruptions.count()
        max_delay = active_disruptions.aggregate(max_d=Sum('estimated_delay_days'))['max_d'] or 0

        # High priority critical action items (top 10 lowest Days of Cover)
        critical_items = (
            InventoryLevel.objects.select_related('product', 'primary_supplier')
            .filter(stock_status__in=[
                InventoryLevel.StockStatus.CRITICAL_STOCKOUT,
                InventoryLevel.StockStatus.WARNING_LOW
            ])
            .order_by('days_of_stock_cover')[:10]
        )

        critical_items_serialized = [
            {
                "sku": item.product.sku,
                "product_name": item.product.name,
                "current_stock": item.current_stock,
                "available_stock": item.available_stock,
                "days_of_stock_cover": float(item.days_of_stock_cover),
                "dynamic_rop": item.dynamic_rop,
                "stock_status": item.stock_status,
                "supplier_name": item.primary_supplier.name if item.primary_supplier else "N/A",
                "supplier_lead_time": item.primary_supplier.lead_time_days if item.primary_supplier else 14,
            }
            for item in critical_items
        ]

        # Recent AI drafted orders
        recent_ai_orders = PurchaseOrder.objects.filter(
            trigger_source=PurchaseOrder.TriggerSource.AI_AGENT
        ).select_related('supplier', 'product').order_by('-created_at')[:5]

        # Competitive Resiliency Scoring (Digital Twin 0-100 index & TTS vs TTR)
        resilience_data = SupplyChainAnalyticsService.calculate_resilience_and_tts_ttr()

        return Response({
            "summary_kpis": {
                "total_tracked_skus": total_skus,
                "critical_stockouts": critical_count,
                "warning_low_stock": warning_count,
                "optimal_stock": optimal_count,
                "overstocked": overstock_count,
                "average_days_of_cover": round(float(avg_cover), 1),
                "pending_ai_purchase_orders": pending_po_count,
                "pending_procurement_value_usd": float(pending_po_value),
                "active_disruption_threats": disruption_count,
                "cumulative_delay_days_flagged": max_delay,
                "digital_twin_resiliency_score": resilience_data["composite_resiliency_score"],
                "resilience_health_label": resilience_data["resilience_health_label"],
                "color_grade": resilience_data["color_grade"],
                "vulnerable_skus_count": resilience_data["critical_vulnerability_count"],
            },
            "urgent_replenishment_queue": critical_items_serialized,
            "recent_ai_drafted_pos": PurchaseOrderSerializer(recent_ai_orders, many=True).data,
            "generated_at": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)


# ==============================================================================
# 2. Action Endpoint: Trigger AI Replenishment & Draft Purchase Order
# ==============================================================================
class TriggerReplenishmentActionView(APIView):
    """
    Action endpoint triggering the collaborative Multi-Agent AI system
    (Demand Agent -> Inventory Agent -> Planning Agent) to evaluate a SKU,
    calculate dynamic days of cover, and draft a PO in 'Pending Approval' state
    alongside its AI Chain-of-Thought reasoning.
    """

    def post(self, request, *args, **kwargs):
        serializer = ReplenishmentTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_sku = serializer.validated_data['product_sku']
        auto_draft_po = serializer.validated_data.get('auto_draft_po', True)
        async_execution = serializer.validated_data.get('async_execution', False)

        # Verify product existence
        if not Product.objects.filter(sku=product_sku).exists():
            return Response(
                {"error": f"Product with SKU '{product_sku}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        if async_execution:
            # Delegate to Celery async worker
            async_result = task_run_replenishment_pipeline.delay(
                product_sku=product_sku,
                auto_draft_po=auto_draft_po
            )
            return Response({
                "message": f"AI Replenishment task queued asynchronously for SKU {product_sku}.",
                "task_id": async_result.id,
                "status": "QUEUED"
            }, status=status.HTTP_202_ACCEPTED)

        # Synchronous execution
        try:
            orchestrator = MultiAgentSupplyChainOrchestrator()
            result = orchestrator.run_replenishment_pipeline(
                product_sku=product_sku,
                auto_draft_po=auto_draft_po
            )
            return Response({
                "message": "Multi-agent cognitive evaluation completed successfully.",
                "data": result
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to execute AI Replenishment: {e}", exc_info=True)
            return Response(
                {"error": f"AI Orchestrator encountered an exception: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==============================================================================
# 3. High-Performance CSV Ingestion Endpoint (Polars Powered)
# ==============================================================================
class CSVDataIngestionView(APIView):
    """
    Ingests CSV datasets (suppliers, products, inventory, sales) using Polars.
    Supports instant synchronous bulk processing or asynchronous Celery background tasks.
    """

    def post(self, request, *args, **kwargs):
        serializer = CSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_type = serializer.validated_data['file_type']
        uploaded_file = serializer.validated_data['file']
        async_processing = serializer.validated_data.get('async_processing', False)

        file_bytes = uploaded_file.read()
        byte_stream = io.BytesIO(file_bytes)

        if async_processing:
            # Persist temporary file to disk for Celery worker consumption
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            celery_task = task_ingest_csv_data.delay(file_type, tmp_path)
            return Response({
                "message": f"CSV ingestion for '{file_type}' dispatched to background worker.",
                "task_id": celery_task.id,
                "status": "QUEUED"
            }, status=status.HTTP_202_ACCEPTED)

        # Synchronous high-speed Polars ingestion
        try:
            if file_type == 'suppliers':
                result = PolarsDataIngestionService.ingest_suppliers_csv(byte_stream)
            elif file_type == 'products':
                result = PolarsDataIngestionService.ingest_products_csv(byte_stream)
            elif file_type == 'inventory':
                result = PolarsDataIngestionService.ingest_inventory_csv(byte_stream)
            elif file_type == 'sales':
                result = PolarsDataIngestionService.ingest_sales_history_csv(byte_stream)
            else:
                return Response({"error": "Invalid file_type"}, status=status.HTTP_400_BAD_REQUEST)

            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Polars CSV ingestion error: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to ingest CSV: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


# ==============================================================================
# 4. Disruption Monitoring Scan Endpoint
# ==============================================================================
class TriggerDisruptionScanView(APIView):
    """
    Triggers simulated global news feed ingestion and RAG risk analysis.
    """

    def post(self, request, *args, **kwargs):
        async_mode = request.data.get('async', False)
        if async_mode:
            task = task_monitor_supplier_disruptions.delay()
            return Response({
                "message": "Predictive Disruption Scan queued.",
                "task_id": task.id
            }, status=status.HTTP_202_ACCEPTED)

        alerts = PredictiveDisruptionMonitor.fetch_and_analyze_news()
        return Response({
            "message": "Disruption scan completed successfully.",
            "alerts_created": len(alerts),
            "alerts": alerts
        }, status=status.HTTP_200_OK)


# ==============================================================================
# 5. Standard CRUD ViewSets
# ==============================================================================
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('sku')
    serializer_class = ProductSerializer
    search_fields = ['sku', 'name', 'category']
    filterset_fields = ['category']


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('name')
    serializer_class = SupplierSerializer
    search_fields = ['name', 'region']
    filterset_fields = ['region', 'is_active']

    @action(detail=True, methods=['get'], url_path='scorecard')
    def scorecard(self, request, pk=None):
        """Returns OTIF performance metrics and tiering for a supplier."""
        supplier = self.get_object()
        data = SupplierScorecardService.evaluate_supplier(supplier)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='scorecards')
    def scorecards_list(self, request):
        """Returns OTIF performance metrics and tiering for all suppliers."""
        data = SupplierScorecardService.evaluate_all_suppliers()
        return Response({"count": len(data), "scorecards": data}, status=status.HTTP_200_OK)


class InventoryLevelViewSet(viewsets.ModelViewSet):
    queryset = InventoryLevel.objects.select_related('product', 'primary_supplier').all().order_by('-updated_at')
    serializer_class = InventoryLevelSerializer
    filterset_fields = ['stock_status']

    @action(detail=True, methods=['post'], url_path='recalculate')
    def recalculate(self, request, pk=None):
        """Action endpoint to run AI pipeline directly on an inventory item."""
        inventory = self.get_object()
        orchestrator = MultiAgentSupplyChainOrchestrator()
        result = orchestrator.run_replenishment_pipeline(product_sku=inventory.product.sku)
        return Response(result, status=status.HTTP_200_OK)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier', 'product').all().order_by('-created_at')
    serializer_class = PurchaseOrderSerializer
    filterset_fields = ['status', 'trigger_source']

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approves a drafted PO for transmission to vendor."""
        po = self.get_object()
        if po.status != PurchaseOrder.POStatus.PENDING_APPROVAL and po.status != PurchaseOrder.POStatus.DRAFT:
            return Response(
                {"error": f"Cannot approve PO with current status: {po.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        po.status = PurchaseOrder.POStatus.APPROVED
        po.approved_by = request.data.get('approved_by', 'Procurement Manager')
        po.approved_at = timezone.now()
        po.save()
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Rejects a drafted PO."""
        po = self.get_object()
        po.status = PurchaseOrder.POStatus.REJECTED
        po.save()
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='export-edi')
    def export_edi(self, request, pk=None):
        """Generates ANSI X12 EDI 850 transaction and ERP payload."""
        po = self.get_object()
        data = EDIGeneratorService.generate_erp_export_payload(po)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='transmit')
    def transmit(self, request, pk=None):
        """Autonomously or manually transmits an approved PO to the supplier via ANSI X12 EDI 850."""
        res = AutonomousExecutionEngine.transmit_purchase_order_by_id(pk)
        if res.get("status") == "ERROR":
            return Response(res, status=status.HTTP_400_BAD_REQUEST)
        return Response(res, status=status.HTTP_200_OK)


class DisruptionAlertViewSet(viewsets.ModelViewSet):
    queryset = DisruptionAlert.objects.select_related('affected_supplier', 'affected_product').all().order_by('-created_at')
    serializer_class = DisruptionAlertSerializer
    filterset_fields = ['severity', 'is_resolved']

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        """Marks a disruption alert as resolved and normalizes risk."""
        alert = self.get_object()
        alert.is_resolved = True
        alert.save()
        return Response({"message": f"Alert {alert.id} resolved."}, status=status.HTTP_200_OK)


# ==============================================================================
# 6. What-If Scenario Stress Testing & Simulation Endpoint
# ==============================================================================
class WhatIfSimulationView(APIView):
    """
    Parametric simulation engine testing supply chain shocks:
    - Demand surge shocks (e.g. +30% or +50%)
    - Shipping and customs congestion (+7 or +14 days)
    - Supplier credit / geopolitical risk escalation
    - Dynamic King-formula safety stock recalculation
    """

    def post(self, request, *args, **kwargs):
        serializer = SimulationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        product_sku = data.get('product_sku')
        if not product_sku:
            prod = Product.objects.first()
            product_sku = prod.sku if prod else "SKU-ELEC-1001"

        if not Product.objects.filter(sku=product_sku).exists():
            return Response(
                {"error": f"Product with SKU '{product_sku}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            simulation_results = SupplyChainSimulator.run_what_if_scenario(
                product_sku=product_sku,
                demand_surge_percent=data.get('demand_surge_percent', 0.0),
                lead_time_delay_days=data.get('lead_time_delay_days', 0),
                supplier_risk_spike=data.get('supplier_risk_spike', 0.0),
                target_service_level=data.get('target_service_level', 0.95),
            )
            return Response(simulation_results, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error running what-if scenario: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==============================================================================
# 7. Semantic Vector Disruption Search (pgvector Powered)
# ==============================================================================
class SemanticDisruptionSearchView(APIView):
    """
    Performs cosine similarity search against stored DisruptionAlerts
    using 1536d vector embeddings.
    """

    def get(self, request, *args, **kwargs):
        query = request.query_params.get('query', '')
        if not query or len(query.strip()) < 2:
            return Response({"error": "Query parameter 'query' is required."}, status=status.HTTP_400_BAD_REQUEST)

        top_k = int(request.query_params.get('top_k', 5))
        results = PredictiveDisruptionMonitor.semantic_search_disruptions(query=query, top_k=top_k)
        return Response({"query": query, "count": len(results), "matches": results}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = SemanticSearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data['query']
        top_k = serializer.validated_data.get('top_k', 5)

        results = PredictiveDisruptionMonitor.semantic_search_disruptions(query=query, top_k=top_k)
        return Response({"query": query, "count": len(results), "matches": results}, status=status.HTTP_200_OK)


# ==============================================================================
# 8. Multi-Echelon & Warehouse ViewSets
# ==============================================================================
class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by('code')
    serializer_class = WarehouseSerializer
    filterset_fields = ['region', 'is_active']


class WarehouseInventoryViewSet(viewsets.ModelViewSet):
    queryset = WarehouseInventory.objects.select_related('warehouse', 'product').all()
    serializer_class = WarehouseInventorySerializer
    filterset_fields = ['warehouse__code', 'product__sku']


class StockTransferRecommendationViewSet(viewsets.ModelViewSet):
    queryset = StockTransferRecommendation.objects.select_related('product', 'source_warehouse', 'target_warehouse').all().order_by('-created_at')
    serializer_class = StockTransferRecommendationSerializer
    filterset_fields = ['status']

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        transfer = self.get_object()
        transfer.status = StockTransferRecommendation.TransferStatus.APPROVED
        transfer.save()
        return Response(StockTransferRecommendationSerializer(transfer).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='execute')
    def execute(self, request, pk=None):
        """Dispatches an inter-warehouse stock transfer, debiting donor inventory and transitioning to IN_TRANSIT."""
        res = AutonomousExecutionEngine.execute_stock_transfer_by_id(pk)
        if res.get("status") == "ERROR":
            return Response(res, status=status.HTTP_400_BAD_REQUEST)
        return Response(res, status=status.HTTP_200_OK)


# ==============================================================================
# 9. Advanced Competitive Analytics (ABC-XYZ, Resilinc TTS/TTR, Slimstock EOQ)
# ==============================================================================
class ABCXYZMatrixView(APIView):
    """
    Blue Yonder / Manhattan Associates Paradigm:
    Classifies catalog into a 9-box ABC-XYZ matrix for segmented replenishment policies.
    """
    def get(self, request, *args, **kwargs):
        data = SupplyChainAnalyticsService.calculate_abc_xyz_matrix()
        return Response(data, status=status.HTTP_200_OK)


class ResilienceTTSView(APIView):
    """
    Resilinc / Everstream Analytics Paradigm:
    Calculates Time-to-Survive (TTS) vs Time-to-Recover (TTR) and overall Digital Twin score.
    """
    def get(self, request, *args, **kwargs):
        data = SupplyChainAnalyticsService.calculate_resilience_and_tts_ttr()
        return Response(data, status=status.HTTP_200_OK)


class EOQOptimizationView(APIView):
    """
    Slimstock / ToolsGroup & Flexport ESG Paradigm:
    Wilson Economic Order Quantity and green freight carbon emissions estimation.
    """
    def get(self, request, *args, **kwargs):
        sku = request.query_params.get('sku')
        if not sku:
            prod = Product.objects.first()
            if not prod:
                return Response({"error": "No products found in catalog"}, status=status.HTTP_404_NOT_FOUND)
            sku = prod.sku

        product = Product.objects.filter(sku=sku).first()
        if not product:
            return Response({"error": f"SKU '{sku}' not found"}, status=status.HTTP_404_NOT_FOUND)

        eoq_data = SupplyChainAnalyticsService.calculate_wilson_eoq_and_cost(product)
        inv = getattr(product, 'inventory_level', None)
        region = inv.primary_supplier.region if inv and inv.primary_supplier else "APAC"
        esg_data = SupplyChainAnalyticsService.calculate_esg_carbon_emissions(
            supplier_region=region,
            order_quantity=eoq_data["recommended_eoq_units"]
        )

        return Response({
            "eoq_analysis": eoq_data,
            "esg_carbon_footprint": esg_data
        }, status=status.HTTP_200_OK)


class PlaybookExecutionView(APIView):
    """
    Newbie-Friendly Interactive Playbooks:
    Allows non-expert users to run guided automated scenarios with 1-click.
    """
    def post(self, request, *args, **kwargs):
        playbook = request.data.get('playbook')

        if playbook == 'port_strike_failover':
            # Simulates Ningbo port strike and runs AI routing
            PredictiveDisruptionMonitor.fetch_and_analyze_news()
            prod = Product.objects.first()
            target_sku = prod.sku if prod else "SKU-ELEC-1001"
            orchestrator = MultiAgentSupplyChainOrchestrator()
            res = orchestrator.run_replenishment_pipeline(target_sku, auto_draft_po=True)
            return Response({
                "playbook": "Port Strike Disruption & Autonomous Vendor Failover",
                "summary": "External port strike flagged in APAC corridor. AI Planning Agent diverted order to backup supplier.",
                "data": res
            }, status=status.HTTP_200_OK)

        elif playbook == 'demand_surge_stress':
            # Runs flash promo surge simulation with King's formula
            prod = Product.objects.first()
            target_sku = prod.sku if prod else "SKU-SENS-2001"
            sim = SupplyChainSimulator.run_what_if_scenario(
                product_sku=target_sku,
                demand_surge_percent=50.0,
                lead_time_delay_days=14,
                target_service_level=0.98
            )
            return Response({
                "playbook": "Black Friday Demand Surge (+50%) Stress Test",
                "summary": "King's formula recalculated dynamic safety stock and warned of imminent stockout.",
                "data": sim
            }, status=status.HTTP_200_OK)

        elif playbook == 'catalog_auto_pilot':
            # Executes multi-agent replenishment across all SKUs, auto-approving safe orders
            from inventory_core.tasks import task_recalculate_all_stock_cover
            summary = task_recalculate_all_stock_cover()
            # Auto-approve POs below $5,000 for trusted suppliers
            approved_count = 0
            for po in PurchaseOrder.objects.filter(status=PurchaseOrder.POStatus.PENDING_APPROVAL):
                if float(po.total_cost) < 5000.0 and po.supplier.risk_score < 0.35:
                    po.status = PurchaseOrder.POStatus.APPROVED
                    po.approved_by = "AI Auto-Pilot Policy (<$5k, Low-Risk)"
                    po.approved_at = timezone.now()
                    po.save()
                    approved_count += 1

            return Response({
                "playbook": "Autonomous Replenishment Auto-Pilot",
                "summary": f"Catalog evaluated. Recalculated DoC and auto-approved {approved_count} low-risk POs under $5,000.",
                "details": summary,
                "auto_approved_orders_count": approved_count
            }, status=status.HTTP_200_OK)

        else:
            return Response({"error": f"Unknown playbook '{playbook}'"}, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# 10. Enterprise Capabilities (Landed Cost, Bullwhip, Obsolescence, Scorecards)
# ==============================================================================
class SupplierScorecardsListView(APIView):
    """
    Returns OTIF and quality scorecard evaluations for all registered suppliers.
    """
    def get(self, request, *args, **kwargs):
        data = SupplierScorecardService.evaluate_all_suppliers()
        return Response({"count": len(data), "scorecards": data}, status=status.HTTP_200_OK)


class LandedCostComparisonView(APIView):
    """
    Computes landed cost breakdown (base + freight + tariffs + insurance + port handling)
    and compares across international and domestic corridors.
    """
    def get(self, request, *args, **kwargs):
        sku = request.query_params.get('sku')
        qty = int(request.query_params.get('quantity', 100))

        if not sku:
            prod = Product.objects.first()
            sku = prod.sku if prod else "SKU-ELEC-1001"

        try:
            data = LandedCostService.compare_supplier_corridors(product_sku=sku, order_quantity=qty)
            return Response(data, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response({"error": f"Product with SKU '{sku}' not found"}, status=status.HTTP_404_NOT_FOUND)


class BullwhipEffectView(APIView):
    """
    Quantifies supply chain variance amplification (Bullwhip Ratio)
    and applies a low-pass order damping filter.
    """
    def get(self, request, *args, **kwargs):
        sku = request.query_params.get('sku')
        if sku:
            product = Product.objects.filter(sku=sku).first()
            if not product:
                return Response({"error": f"SKU '{sku}' not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(BullwhipSuppressionService.analyze_bullwhip_effect(product), status=status.HTTP_200_OK)

        data = BullwhipSuppressionService.analyze_catalog_bullwhip()
        return Response({"catalog_count": len(data), "bullwhip_analysis": data}, status=status.HTTP_200_OK)


class ObsolescenceRiskView(APIView):
    """
    Monitors capital at risk of expiration or shelf-life obsolescence
    when Days of Cover exceeds remaining product lifecycle.
    """
    def get(self, request, *args, **kwargs):
        sku = request.query_params.get('sku')
        if sku:
            product = Product.objects.filter(sku=sku).first()
            if not product:
                return Response({"error": f"SKU '{sku}' not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(ObsolescenceMonitorService.evaluate_obsolescence_risk(product), status=status.HTTP_200_OK)

        data = ObsolescenceMonitorService.scan_catalog_obsolescence()
        return Response(data, status=status.HTTP_200_OK)


# ==============================================================================
# 11. Autonomous Auto-Pilot Controllers & Audit Feeds
# ==============================================================================
class AutoPilotStatusView(APIView):
    """
    Manages autonomous auto-pilot operational status and policy guardrails.
    """
    def get(self, request, *args, **kwargs):
        data = AutonomousExecutionEngine.get_status()
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        payload = request.data
        policy = AutonomousExecutionEngine.update_policy(
            is_enabled=payload.get('is_enabled'),
            max_auto_po_value=payload.get('max_auto_po_value'),
            min_supplier_reliability=payload.get('min_supplier_reliability'),
            auto_execute_transfers=payload.get('auto_execute_transfers'),
            auto_transmit_edi=payload.get('auto_transmit_edi'),
            auto_failover_on_disruption=payload.get('auto_failover_on_disruption'),
        )
        data = AutonomousExecutionEngine.get_status()
        return Response({
            "status": "SUCCESS",
            "message": f"Autonomous Auto-Pilot policy updated. State: {'ACTIVE' if policy.is_enabled else 'PAUSED'}",
            "policy": data
        }, status=status.HTTP_200_OK)


class AutoPilotRunCycleView(APIView):
    """
    Immediately triggers a full autonomous cycle: cognitive evaluation across all
    catalog SKUs, automated transfer dispatch, and zero-touch PO transmission.
    """
    def post(self, request, *args, **kwargs):
        force = request.data.get('force', True)
        result = AutonomousExecutionEngine.run_autonomous_cycle(force=force)
        return Response(result, status=status.HTTP_200_OK)


class AutonomousAuditLogsView(APIView):
    """
    Returns immutable audit trail of automated actions (EDI transmissions, transfers, safety stops).
    """
    def get(self, request, *args, **kwargs):
        from inventory_core.models import AutonomousActionLog
        limit = int(request.query_params.get('limit', 50))
        action_type = request.query_params.get('action_type')

        qs = AutonomousActionLog.objects.all().order_by('-created_at')
        if action_type:
            qs = qs.filter(action_type=action_type)

        logs = qs[:limit]
        data = [
            {
                "id": str(log.id),
                "action_type": log.action_type,
                "reference_code": log.reference_code,
                "product_sku": log.product_sku,
                "headline": log.headline,
                "details": log.details,
                "financial_impact_usd": float(log.financial_impact_usd),
                "status": log.status,
                "has_edi": bool(log.edi_payload),
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
        return Response({"count": len(data), "logs": data}, status=status.HTTP_200_OK)


# ==============================================================================
# 11. Unique Next-Gen AI Features (Copilot, Revenue Shield, Supplier Negotiator)
# ==============================================================================
class AICopilotView(APIView):
    """
    Plain English Executive Copilot: Answers questions about stockout hazards,
    capital requirements, supplier reliability, and auto-pilot execution.
    """
    def post(self, request, *args, **kwargs):
        from inventory_core.services.copilot import StockSenseCopilot
        query = request.data.get('query', '')
        if not query or len(query.strip()) < 2:
            query = "What is the overall state of my supply chain?"
        response_data = StockSenseCopilot.ask(query)
        return Response(response_data, status=status.HTTP_200_OK)


class RevenueRiskShieldView(APIView):
    """
    Translates inventory deficits into direct executive financial impact:
    Lost Revenue, Lost Gross Margin, and Wasted Paid Ad Spend.
    """
    def get(self, request, *args, **kwargs):
        from inventory_core.services.revenue_risk import RevenueRiskEngine
        data = RevenueRiskEngine.evaluate_catalog_financial_exposure()
        return Response(data, status=status.HTTP_200_OK)


class AIVolumeNegotiatorView(APIView):
    """
    Evaluates tiered volume discount arbitrage opportunities and generates
    an executive supplier negotiation email to capture margin gains.
    """
    def post(self, request, *args, **kwargs):
        from inventory_core.services.ai_negotiator import AIVolumeDiscountArbitrageur
        sku = request.data.get('product_sku')
        if not sku:
            prod = Product.objects.first()
            sku = prod.sku if prod else "SKU-ELEC-1001"
        qty = int(request.data.get('planned_order_qty', 0))

        try:
            result = AIVolumeDiscountArbitrageur.analyze_discount_arbitrage(
                product_sku=sku,
                planned_order_qty=qty
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)





