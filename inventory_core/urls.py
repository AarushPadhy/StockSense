"""
URL Routing for Inventory Core API & Dashboard.
"""

from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from inventory_core.api import (
    ProductViewSet,
    SupplierViewSet,
    InventoryLevelViewSet,
    PurchaseOrderViewSet,
    DisruptionAlertViewSet,
    WarehouseViewSet,
    WarehouseInventoryViewSet,
    StockTransferRecommendationViewSet,
    ReplenishmentDashboardView,
    TriggerReplenishmentActionView,
    CSVDataIngestionView,
    TriggerDisruptionScanView,
    WhatIfSimulationView,
    SemanticDisruptionSearchView,
    ABCXYZMatrixView,
    ResilienceTTSView,
    EOQOptimizationView,
    PlaybookExecutionView,
    SupplierScorecardsListView,
    LandedCostComparisonView,
    BullwhipEffectView,
    ObsolescenceRiskView,
    AutoPilotStatusView,
    AutoPilotRunCycleView,
    AutonomousAuditLogsView,
    AICopilotView,
    RevenueRiskShieldView,
    AIVolumeNegotiatorView,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'inventory', InventoryLevelViewSet, basename='inventory')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'disruptions', DisruptionAlertViewSet, basename='disruption')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'warehouse-inventory', WarehouseInventoryViewSet, basename='warehouse-inventory')
router.register(r'stock-transfers', StockTransferRecommendationViewSet, basename='stock-transfer')

urlpatterns = [
    # Explicit custom non-CRUD paths (routed before default router)
    path('suppliers/scorecards/', SupplierScorecardsListView.as_view(), name='supplier-scorecards-list'),

    # Router endpoints (CRUD + custom detail actions)
    path('', include(router.urls)),

    # Replenishment Telemetry & Analytics Dashboard
    path('dashboard/replenishment/', ReplenishmentDashboardView.as_view(), name='replenishment-dashboard'),

    # Autonomous Multi-Agent Action Trigger
    path('replenishment/draft-po/', TriggerReplenishmentActionView.as_view(), name='trigger-draft-po'),

    # High-Performance Polars Ingestion
    path('ingestion/upload-csv/', CSVDataIngestionView.as_view(), name='upload-csv-ingestion'),

    # External Disruption Monitor & RAG Scan
    path('disruptions/trigger-scan/', TriggerDisruptionScanView.as_view(), name='trigger-disruption-scan'),

    # What-If Scenario Simulation
    path('simulation/what-if/', WhatIfSimulationView.as_view(), name='what-if-simulation'),

    # Semantic Vector Search (pgvector)
    path('disruptions/semantic-search/', SemanticDisruptionSearchView.as_view(), name='semantic-disruption-search'),

    # Advanced Competitive Analytics & Matrix Views
    path('analytics/abc-xyz/', ABCXYZMatrixView.as_view(), name='analytics-abc-xyz'),
    path('analytics/resilience-tts/', ResilienceTTSView.as_view(), name='analytics-resilience-tts'),
    path('analytics/tts-ttr/', ResilienceTTSView.as_view(), name='analytics-tts-ttr-alias'),
    path('analytics/eoq/', EOQOptimizationView.as_view(), name='analytics-eoq'),

    # Newbie-Friendly Interactive Playbooks
    path('playbooks/execute/', PlaybookExecutionView.as_view(), name='playbook-execute'),

    # Enterprise Scorecards, Landed Cost, Bullwhip & Obsolescence
    path('analytics/landed-cost/', LandedCostComparisonView.as_view(), name='analytics-landed-cost'),
    path('analytics/bullwhip/', BullwhipEffectView.as_view(), name='analytics-bullwhip'),
    path('analytics/obsolescence-risk/', ObsolescenceRiskView.as_view(), name='analytics-obsolescence-risk'),

    # Autonomous Auto-Pilot & Execution Engine
    path('automation/status/', AutoPilotStatusView.as_view(), name='automation-status'),
    path('automation/toggle/', AutoPilotStatusView.as_view(), name='automation-toggle'),
    path('automation/run-cycle/', AutoPilotRunCycleView.as_view(), name='automation-run-cycle'),
    path('automation/audit-logs/', AutonomousAuditLogsView.as_view(), name='automation-audit-logs'),

    # Next-Gen Unique AI Features
    path('ai/copilot/', AICopilotView.as_view(), name='ai-copilot'),
    path('ai/revenue-at-risk/', RevenueRiskShieldView.as_view(), name='ai-revenue-at-risk'),
    path('ai/negotiate/', AIVolumeNegotiatorView.as_view(), name='ai-negotiate'),
]
