"""
Celery Asynchronous Tasks for Supply Chain & Inventory Optimization.

Provides background job execution for:
1. High-speed CSV ingestion using Polars.
2. Multi-agent dynamic stock cover and PO drafting routines.
3. Predictive disruption monitoring and RAG risk analysis.
"""

import logging
from celery import shared_task
from inventory_core.services.ingestion import PolarsDataIngestionService
from inventory_core.services.ai_agents import MultiAgentSupplyChainOrchestrator
from inventory_core.services.disruption_monitor import PredictiveDisruptionMonitor
from inventory_core.services.automation_engine import AutonomousExecutionEngine
from inventory_core.models import Product

logger = logging.getLogger(__name__)


# ==============================================================================
# Ingestion Tasks
# ==============================================================================
@shared_task(name='inventory_core.tasks.task_ingest_csv_data')
def task_ingest_csv_data(file_type: str, file_path: str):
    """
    Asynchronously ingests CSV data using Polars.
    file_type options: 'suppliers', 'products', 'inventory', 'sales'
    """
    logger.info(f"Celery task started: Ingesting {file_type} from {file_path}")
    try:
        if file_type == 'suppliers':
            result = PolarsDataIngestionService.ingest_suppliers_csv(file_path)
        elif file_type == 'products':
            result = PolarsDataIngestionService.ingest_products_csv(file_path)
        elif file_type == 'inventory':
            result = PolarsDataIngestionService.ingest_inventory_csv(file_path)
        elif file_type == 'sales':
            result = PolarsDataIngestionService.ingest_sales_history_csv(file_path)
        else:
            raise ValueError(f"Unknown file_type '{file_type}'")

        logger.info(f"Celery ingestion completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error during async CSV ingestion: {str(e)}", exc_info=True)
        return {"status": "ERROR", "error": str(e)}


# ==============================================================================
# Multi-Agent Replenishment Tasks
# ==============================================================================
@shared_task(name='inventory_core.tasks.task_run_replenishment_pipeline')
def task_run_replenishment_pipeline(product_sku: str, auto_draft_po: bool = True):
    """
    Triggers the 3-agent cognitive loop (Demand Agent -> Inventory Agent -> Planning Agent)
    for a specific SKU, dynamically updating Days of Stock Cover and drafting a PO if needed.
    """
    logger.info(f"Celery task started: AI Replenishment pipeline for SKU {product_sku}")
    try:
        orchestrator = MultiAgentSupplyChainOrchestrator()
        result = orchestrator.run_replenishment_pipeline(
            product_sku=product_sku,
            auto_draft_po=auto_draft_po
        )
        logger.info(f"AI Replenishment pipeline finished for SKU {product_sku}")
        return result
    except Exception as e:
        logger.error(f"Failed to execute replenishment pipeline for SKU {product_sku}: {e}", exc_info=True)
        return {"status": "ERROR", "sku": product_sku, "error": str(e)}


@shared_task(name='inventory_core.tasks.task_recalculate_all_stock_cover')
def task_recalculate_all_stock_cover():
    """
    Batch periodic routine (e.g., daily) to update dynamic Days of Cover
    and identify impending stock-out risks across the entire product catalog.
    """
    logger.info("Celery task started: Catalog-wide Stock Cover recalculation")
    orchestrator = MultiAgentSupplyChainOrchestrator()
    skus = list(Product.objects.values_list('sku', flat=True))
    
    summary = {
        "processed": 0,
        "critical_stockouts": 0,
        "warnings": 0,
        "orders_drafted": 0
    }

    for sku in skus:
        try:
            res = orchestrator.run_replenishment_pipeline(product_sku=sku, auto_draft_po=True)
            summary["processed"] += 1
            inv_status = res.get("inventory_health", {}).get("stock_status")
            if inv_status == "CRITICAL_STOCKOUT":
                summary["critical_stockouts"] += 1
            elif inv_status == "WARNING_LOW":
                summary["warnings"] += 1

            if res.get("purchase_order_drafted"):
                summary["orders_drafted"] += 1
        except Exception as e:
            logger.error(f"Error calculating stock cover for SKU {sku}: {e}")

    logger.info(f"Catalog-wide Stock Cover recalculation completed: {summary}")
    return summary


# ==============================================================================
# Disruption Monitoring Tasks
# ==============================================================================
@shared_task(name='inventory_core.tasks.task_monitor_supplier_disruptions')
def task_monitor_supplier_disruptions():
    """
    Periodic background job fetching global news feeds, executing RAG
    semantic risk analysis, and raising DisruptionAlerts for impacted suppliers.
    """
    logger.info("Celery task started: Supplier Disruption & News Feed RAG Scan")
    try:
        alerts = PredictiveDisruptionMonitor.fetch_and_analyze_news()
        return {
            "status": "SUCCESS",
            "alerts_created_count": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Error monitoring supplier disruptions: {e}", exc_info=True)
        return {"status": "ERROR", "error": str(e)}


# ==============================================================================
# Autonomous Auto-Pilot Cycle Routine
# ==============================================================================
@shared_task(name='inventory_core.tasks.task_run_autonomous_cycle')
def task_run_autonomous_cycle(force: bool = False):
    """
    Periodic autonomous routine: evaluates inventory risks, auto-dispatches
    inter-warehouse transfers, auto-approves POs within budget guardrails,
    and transmits ANSI X12 EDI 850 orders directly to suppliers.
    """
    logger.info("Celery task started: Autonomous Auto-Pilot Execution Cycle")
    try:
        report = AutonomousExecutionEngine.run_autonomous_cycle(force=force)
        logger.info(f"Autonomous cycle completed: {report.get('total_actions_executed')} actions executed")
        return report
    except Exception as e:
        logger.error(f"Error running autonomous cycle: {e}", exc_info=True)
        return {"status": "ERROR", "error": str(e)}

