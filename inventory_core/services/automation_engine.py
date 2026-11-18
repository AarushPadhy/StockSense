"""
Autonomous Auto-Pilot Execution Engine.

Enterprise Autonomy Feature:
Moves the platform from passive recommendations to ACTIVE autonomous execution.
When enabled, Auto-Pilot:
1. Sweeps all product inventory positions using the multi-agent cognitive loop.
2. Auto-executes stock transfers between distribution hubs, deducting donor stock
   and switching state to IN_TRANSIT.
3. Auto-approves and transmits purchase orders to suppliers via ANSI X12 EDI 850,
   guarded by configurable financial ceilings and vendor reliability scores.
4. Generates an immutable, transparent AutonomousActionLog audit feed.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction

from inventory_core.models import (
    Product,
    PurchaseOrder,
    StockTransferRecommendation,
    WarehouseInventory,
    AutoPilotPolicy,
    AutonomousActionLog,
)
from inventory_core.services.ai_agents import MultiAgentSupplyChainOrchestrator
from inventory_core.services.edi_generator import EDIGeneratorService

logger = logging.getLogger(__name__)


class AutonomousExecutionEngine:
    """
    Central operational controller for zero-touch autonomous replenishment,
    order transmission, and multi-echelon stock dispatch.
    """

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        Retrieves real-time telemetry on the auto-pilot engine.
        """
        policy = AutoPilotPolicy.get_active_policy()
        
        pending_pos = PurchaseOrder.objects.filter(status=PurchaseOrder.POStatus.PENDING_APPROVAL).count()
        transmitted_pos = PurchaseOrder.objects.filter(status=PurchaseOrder.POStatus.TRANSMITTED).count()
        recommended_transfers = StockTransferRecommendation.objects.filter(
            status=StockTransferRecommendation.TransferStatus.RECOMMENDED
        ).count()
        in_transit_transfers = StockTransferRecommendation.objects.filter(
            status=StockTransferRecommendation.TransferStatus.IN_TRANSIT
        ).count()
        
        recent_logs = list(AutonomousActionLog.objects.all()[:10].values(
            'id', 'action_type', 'reference_code', 'product_sku', 'headline',
            'details', 'financial_impact_usd', 'status', 'created_at'
        ))

        return {
            "is_enabled": policy.is_enabled,
            "policy_name": policy.name,
            "max_auto_po_value_usd": float(policy.max_auto_po_value),
            "min_supplier_reliability": policy.min_supplier_reliability,
            "auto_execute_transfers": policy.auto_execute_transfers,
            "auto_transmit_edi": policy.auto_transmit_edi,
            "auto_failover_on_disruption": policy.auto_failover_on_disruption,
            "total_automated_actions": policy.total_automated_actions,
            "total_automated_spend_usd": float(policy.total_automated_spend_usd),
            "last_run_at": policy.last_run_at.isoformat() if policy.last_run_at else None,
            "queue_stats": {
                "pending_approval_pos": pending_pos,
                "transmitted_pos": transmitted_pos,
                "pending_transfers": recommended_transfers,
                "in_transit_transfers": in_transit_transfers,
            },
            "recent_audit_trail": recent_logs,
        }

    @classmethod
    def update_policy(
        cls,
        is_enabled: Optional[bool] = None,
        max_auto_po_value: Optional[float] = None,
        min_supplier_reliability: Optional[float] = None,
        auto_execute_transfers: Optional[bool] = None,
        auto_transmit_edi: Optional[bool] = None,
        auto_failover_on_disruption: Optional[bool] = None,
    ) -> AutoPilotPolicy:
        """
        Updates governance guardrails for autonomous execution.
        """
        policy = AutoPilotPolicy.get_active_policy()
        if is_enabled is not None:
            policy.is_enabled = bool(is_enabled)
        if max_auto_po_value is not None:
            policy.max_auto_po_value = Decimal(str(max_auto_po_value))
        if min_supplier_reliability is not None:
            policy.min_supplier_reliability = float(min_supplier_reliability)
        if auto_execute_transfers is not None:
            policy.auto_execute_transfers = bool(auto_execute_transfers)
        if auto_transmit_edi is not None:
            policy.auto_transmit_edi = bool(auto_transmit_edi)
        if auto_failover_on_disruption is not None:
            policy.auto_failover_on_disruption = bool(auto_failover_on_disruption)

        policy.save()
        logger.info(f"AutoPilotPolicy updated: Enabled={policy.is_enabled}, MaxPO=${policy.max_auto_po_value}")
        return policy

    @classmethod
    def run_autonomous_cycle(cls, force: bool = False) -> Dict[str, Any]:
        """
        Executes a complete autonomous replenishment and fulfillment sweep.
        Runs multi-agent replenishment pipeline on all SKUs, executes qualifying
        warehouse transfers, auto-approves and transmits POs with ANSI X12 EDI 850.
        """
        policy = AutoPilotPolicy.get_active_policy()
        if not policy.is_enabled and not force:
            return {
                "status": "PAUSED",
                "message": "Autonomous Auto-Pilot is currently paused. Toggle ON or pass force=True to execute.",
                "actions_executed": 0,
            }

        orchestrator = MultiAgentSupplyChainOrchestrator()
        products = list(Product.objects.all())

        executed_pos: List[Dict[str, Any]] = []
        executed_transfers: List[Dict[str, Any]] = []
        held_orders: List[Dict[str, Any]] = []
        total_cycle_spend = Decimal('0.00')

        for product in products:
            try:
                # 1. Run Cognitive Multi-Agent Replenishment Pipeline
                pipeline_res = orchestrator.run_replenishment_pipeline(
                    product_sku=product.sku,
                    auto_draft_po=True
                )
                plan = pipeline_res.get("procurement_plan", {})
                action = plan.get("action")

                # 2. Check if an Inter-Warehouse Transfer was recommended or pending
                if policy.auto_execute_transfers:
                    pending_recs = list(StockTransferRecommendation.objects.filter(
                        product=product,
                        status=StockTransferRecommendation.TransferStatus.RECOMMENDED
                    ))
                    for rec in pending_recs:
                        dispatch_res = cls._execute_transfer_internal(rec, automated=True)
                        if dispatch_res.get("status") == "IN_TRANSIT":
                            executed_transfers.append(dispatch_res)

                # 3. Check if a Purchase Order was drafted or is pending approval
                if action in ["DRAFT_PO", "EXPEDITE_PO"]:
                    latest_po = PurchaseOrder.objects.filter(
                        product=product,
                        status=PurchaseOrder.POStatus.PENDING_APPROVAL
                    ).order_by('-created_at').first()

                    if latest_po:
                        po_cost = latest_po.total_cost
                        vendor_rel = latest_po.supplier.reliability_rating

                        # Guardrail Check 1: Maximum PO Value Limit
                        within_budget = po_cost <= policy.max_auto_po_value
                        # Guardrail Check 2: Supplier Reliability Minimum
                        vendor_qualified = vendor_rel >= policy.min_supplier_reliability

                        if within_budget and vendor_qualified:
                            # Autonomous Approval & EDI Transmission
                            transmit_res = cls._execute_po_transmission_internal(latest_po, policy, automated=True)
                            executed_pos.append(transmit_res)
                            total_cycle_spend += po_cost
                        else:
                            # Held for Human Sign-off (Safety Ceiling)
                            reason_tokens = []
                            if not within_budget:
                                reason_tokens.append(f"Cost ${po_cost:,.2f} exceeds auto ceiling ${policy.max_auto_po_value:,.2f}")
                            if not vendor_qualified:
                                reason_tokens.append(f"Supplier reliability {vendor_rel:.2f} < {policy.min_supplier_reliability:.2f}")

                            headline = f"Held {latest_po.po_number} for Human Sign-off"
                            details = f"Safety guardrail triggered: {', '.join(reason_tokens)}. Order prepared with full AI reasoning."
                            
                            AutonomousActionLog.objects.create(
                                action_type=AutonomousActionLog.ActionType.GUARDRAIL_HELD,
                                reference_code=latest_po.po_number,
                                product_sku=product.sku,
                                headline=headline,
                                details=details,
                                financial_impact_usd=po_cost,
                                status="HELD_FOR_REVIEW"
                            )

                            held_orders.append({
                                "po_number": latest_po.po_number,
                                "sku": product.sku,
                                "supplier": latest_po.supplier.name,
                                "total_cost": float(po_cost),
                                "reasons": reason_tokens
                            })

            except Exception as e:
                logger.error(f"Error in autonomous replenishment for SKU {product.sku}: {e}", exc_info=True)

        # Update Master Policy Counters
        total_actions = len(executed_pos) + len(executed_transfers)
        policy.total_automated_actions += total_actions
        policy.total_automated_spend_usd += total_cycle_spend
        policy.last_run_at = timezone.now()
        policy.save()

        return {
            "status": "COMPLETED",
            "cycle_timestamp": policy.last_run_at.isoformat(),
            "total_products_scanned": len(products),
            "total_actions_executed": total_actions,
            "total_cycle_spend_usd": float(total_cycle_spend),
            "executed_purchase_orders_count": len(executed_pos),
            "executed_transfers_count": len(executed_transfers),
            "held_for_human_review_count": len(held_orders),
            "executed_purchase_orders": executed_pos,
            "executed_stock_transfers": executed_transfers,
            "held_orders": held_orders,
        }

    @classmethod
    def _execute_po_transmission_internal(
        cls,
        po: PurchaseOrder,
        policy: AutoPilotPolicy,
        automated: bool = True
    ) -> Dict[str, Any]:
        """
        Transitions PurchaseOrder to TRANSMITTED, generates EDI 850, and logs action.
        """
        with transaction.atomic():
            po.status = PurchaseOrder.POStatus.TRANSMITTED
            po.approved_by = "AI_AUTONOMOUS_AUTOPILOT" if automated else "OPERATOR_OVERRIDE"
            po.approved_at = timezone.now()
            po.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])

            # Generate ANSI X12 EDI 850 format payload
            edi_text = EDIGeneratorService.generate_edi_850(po)

            headline = f"Autonomously Approved & Transmitted {po.po_number}"
            details = (
                f"Generated ANSI X12 EDI 850 ({po.quantity} units, ${float(po.total_cost):,.2f}). "
                f"Transmitted to {po.supplier.name} with expected delivery in {po.supplier.lead_time_days} days. "
                f"AI Justification: {po.ai_reasoning[:200]}..."
            )

            AutonomousActionLog.objects.create(
                action_type=AutonomousActionLog.ActionType.PO_TRANSMITTED,
                reference_code=po.po_number,
                product_sku=po.product.sku,
                headline=headline,
                details=details,
                financial_impact_usd=po.total_cost,
                edi_payload=edi_text,
                status="TRANSMITTED"
            )

        return {
            "po_number": po.po_number,
            "sku": po.product.sku,
            "supplier": po.supplier.name,
            "quantity": po.quantity,
            "total_cost": float(po.total_cost),
            "status": "TRANSMITTED",
            "edi_850_generated": True,
        }

    @classmethod
    def _execute_transfer_internal(
        cls,
        transfer: StockTransferRecommendation,
        automated: bool = True
    ) -> Dict[str, Any]:
        """
        Executes inter-warehouse inventory rebalancing by debiting donor warehouse
        and transitioning status to IN_TRANSIT.
        """
        with transaction.atomic():
            # Check source warehouse inventory
            source_pos = WarehouseInventory.objects.filter(
                warehouse=transfer.source_warehouse,
                product=transfer.product
            ).first()

            if source_pos and source_pos.current_stock >= transfer.quantity:
                source_pos.current_stock -= transfer.quantity
                source_pos.save(update_fields=['current_stock', 'updated_at'])

            transfer.status = StockTransferRecommendation.TransferStatus.IN_TRANSIT
            transfer.save(update_fields=['status', 'updated_at'])

            headline = f"Autonomous Stock Transfer: {transfer.quantity}x {transfer.product.sku} Dispatched"
            details = (
                f"Transferred from {transfer.source_warehouse.code} ({transfer.source_warehouse.name}) "
                f"to {transfer.target_warehouse.code} ({transfer.target_warehouse.name}). "
                f"Transit time: {transfer.estimated_transit_days} days. Saved ${float(transfer.cost_savings_usd):,.2f} vs emergency air freight."
            )

            AutonomousActionLog.objects.create(
                action_type=AutonomousActionLog.ActionType.TRANSFER_DISPATCHED,
                reference_code=str(transfer.id)[:8].upper(),
                product_sku=transfer.product.sku,
                headline=headline,
                details=details,
                financial_impact_usd=transfer.cost_savings_usd,
                status="IN_TRANSIT"
            )

        return {
            "transfer_id": str(transfer.id),
            "sku": transfer.product.sku,
            "source_warehouse": transfer.source_warehouse.code,
            "target_warehouse": transfer.target_warehouse.code,
            "quantity": transfer.quantity,
            "cost_savings_usd": float(transfer.cost_savings_usd),
            "status": "IN_TRANSIT",
        }

    @classmethod
    def transmit_purchase_order_by_id(cls, po_id: str) -> Dict[str, Any]:
        """
        Direct execution endpoint for an individual purchase order.
        """
        po = PurchaseOrder.objects.filter(id=po_id).first()
        if not po:
            return {"status": "ERROR", "message": f"PurchaseOrder with ID {po_id} not found"}

        policy = AutoPilotPolicy.get_active_policy()
        res = cls._execute_po_transmission_internal(po, policy, automated=False)
        return {"status": "SUCCESS", "data": res}

    @classmethod
    def execute_stock_transfer_by_id(cls, transfer_id: str) -> Dict[str, Any]:
        """
        Direct execution endpoint for an individual stock transfer.
        """
        transfer = StockTransferRecommendation.objects.filter(id=transfer_id).first()
        if not transfer:
            return {"status": "ERROR", "message": f"Transfer with ID {transfer_id} not found"}

        res = cls._execute_transfer_internal(transfer, automated=False)
        return {"status": "SUCCESS", "data": res}
