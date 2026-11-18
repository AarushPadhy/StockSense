"""
Multi-Agent AI Supply Chain Orchestrator.

Architectural Design & State Transitions:
------------------------------------------
Three specialized, autonomous AI agents collaborate in a sequential cognitive pipeline:

1. Demand Agent:
   - Input: Product metadata + historical SalesHistory time-series.
   - Role: Extracts demand velocity, trend slope, empirical EWMA projections, and predicts
     short-term daily demand over the replenishment horizon.
   - Output: DemandState (forecasted daily demand, trend classification, demand volatility).

2. Inventory Agent:
   - Input: DemandState + real-time InventoryLevel (on-hand, allocated, safety stock).
   - Role: Calculates dynamic Days of Stock Cover (DoC = available_stock / forecasted_daily_demand).
     Compares DoC against dynamic supplier lead times to flag exact stock-out or overstock risks.
     Recalculates dynamic Reorder Point (Dynamic ROP).
   - Output: InventoryHealthState (DoC, stock status, shortfall units, urgency).

3. Planning Agent:
   - Input: InventoryHealthState + Supplier profile (lead time, risk rating) + DisruptionAlerts.
   - Role: Synthesizes risk tradeoffs, checks alternative suppliers if primary supplier is high-risk,
     determines exact optimal purchase quantity (respecting MOQs), and formulates multi-step
     procurement strategies.
   - Output: ProcurementDecision (action recommendation, PO draft parameters, AI Chain-of-Thought reasoning).
"""

import os
import uuid
import json
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from django.utils import timezone
from django.conf import settings

from inventory_core.models import (
    Product,
    Supplier,
    InventoryLevel,
    PurchaseOrder,
    DisruptionAlert,
)
from inventory_core.services.forecasting import DemandForecaster

logger = logging.getLogger(__name__)


# ==============================================================================
# Pipeline State Schemas (Type-safe Inter-Agent Contract)
# ==============================================================================
@dataclass
class DemandState:
    sku: str
    product_name: str
    mean_daily_sales: float
    std_daily_sales: float
    trend_slope: float
    trend_category: str
    forecasted_daily_demand: float
    forecast_horizon_days: int
    confidence_interval_95: tuple
    agent_insights: str


@dataclass
class InventoryHealthState:
    sku: str
    current_stock: int
    allocated_stock: int
    available_stock: int
    safety_stock: int
    forecasted_daily_demand: float
    days_of_stock_cover: float
    effective_lead_time_days: int
    is_stockout_imminent: bool
    is_overstocked: bool
    stock_status: str
    dynamic_rop: int
    agent_reasoning: str


@dataclass
class ProcurementRecommendation:
    sku: str
    supplier_id: Optional[str]
    supplier_name: Optional[str]
    action: str  # DRAFT_PO, EXPEDITE, HOLD, REALLOCATE
    recommended_order_quantity: int
    estimated_total_cost: Decimal
    urgency_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    ai_chain_of_thought: str
    risk_summary: str
    alternative_supplier_recommended: bool
    alternative_supplier_name: Optional[str] = None


# ==============================================================================
# Agent 1: Demand Agent
# ==============================================================================
class DemandAgent:
    """
    Analyzes historical sales time-series to formulate dynamic demand projections.
    Blends statistical baselines with AI reasoning to capture trend shifts.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or getattr(settings, 'LLM_MODEL_NAME', 'gpt-4o-mini')

    def analyze_demand(self, product: Product, forecast_horizon_days: int = 14) -> DemandState:
        """
        Executes statistical forecasting baseline and synthesizes qualitative demand trends.
        """
        # Step 1: Compute statistical time-series metrics from SalesHistory
        stats = DemandForecaster.analyze_product_demand(
            product=product,
            lookback_days=90,
            forecast_horizon_days=forecast_horizon_days
        )

        daily_demand = stats["forecasted_daily_demand"]
        trend = stats["demand_trend_category"]
        slope = stats["trend_slope"]

        # Step 2: Formulate Agent Chain-of-Thought insight
        if trend == "EXPANDING_GROWTH":
            insight = (
                f"Demand acceleration detected for SKU {product.sku}. "
                f"Sales velocity increased with a positive trend slope (+{slope:.3f} units/day). "
                f"Projected daily burn rate updated to {daily_demand:.1f} units/day."
            )
        elif trend == "CONTRACTING_DECAY":
            insight = (
                f"Demand deceleration observed for SKU {product.sku} (slope: {slope:.3f} units/day). "
                f"Projected consumption normalized to {daily_demand:.1f} units/day to avoid over-purchasing."
            )
        elif trend == "COLD_START_BASELINE":
            insight = (
                f"Insufficient historical transactions for SKU {product.sku}. "
                f"Operating on baseline Reorder Point heuristic ({daily_demand:.1f} units/day)."
            )
        else:
            insight = (
                f"Stable consumption pattern observed for SKU {product.sku}. "
                f"Daily projected demand estimated at {daily_demand:.1f} units/day (EWMA blended)."
            )

        return DemandState(
            sku=product.sku,
            product_name=product.name,
            mean_daily_sales=stats["mean_daily_sales"],
            std_daily_sales=stats["std_daily_sales"],
            trend_slope=stats["trend_slope"],
            trend_category=trend,
            forecasted_daily_demand=daily_demand,
            forecast_horizon_days=forecast_horizon_days,
            confidence_interval_95=stats["confidence_interval_95"],
            agent_insights=insight
        )


# ==============================================================================
# Agent 2: Inventory Agent
# ==============================================================================
class InventoryAgent:
    """
    Evaluates current inventory against dynamic demand burn rate and lead times.
    Calculates Days of Stock Cover (DoC) and pinpoints stockout or excess inventory hazards.
    """

    def evaluate_inventory_health(
        self,
        inventory: InventoryLevel,
        demand_state: DemandState,
        active_disruptions: List[DisruptionAlert]
    ) -> InventoryHealthState:
        """
        Calculates dynamic Days of Cover and categorizes stock risk.
        """
        daily_demand = max(0.1, demand_state.forecasted_daily_demand)
        available_stock = inventory.available_stock

        # Calculate dynamic Days of Stock Cover (DoC)
        days_of_cover = round(available_stock / daily_demand, 2)

        # Base supplier lead time + cumulative disruption delay days
        base_lead_time = (
            inventory.primary_supplier.lead_time_days
            if inventory.primary_supplier else 14
        )
        disruption_delay = sum(
            d.estimated_delay_days for d in active_disruptions if not d.is_resolved
        )
        effective_lead_time = base_lead_time + disruption_delay

        # Dynamic Reorder Point calculation:
        # Dynamic ROP = (Daily Demand * Effective Lead Time) + Safety Stock
        dynamic_rop = int(round((daily_demand * effective_lead_time) + inventory.safety_stock))

        # Risk Classification Logic
        is_stockout_imminent = False
        is_overstocked = False

        if days_of_cover <= effective_lead_time:
            # Current inventory will run dry BEFORE a newly placed order could arrive!
            stock_status = InventoryLevel.StockStatus.CRITICAL_STOCKOUT
            is_stockout_imminent = True
            reasoning = (
                f"CRITICAL DEFICIT: Current stock cover ({days_of_cover:.1f} days) is less than or equal "
                f"to effective supplier lead time ({effective_lead_time} days, including {disruption_delay}d disruption). "
                f"Immediate stock-out will occur without emergency replenishment."
            )
        elif available_stock <= dynamic_rop:
            # Stock is below dynamic reorder threshold
            stock_status = InventoryLevel.StockStatus.WARNING_LOW
            reasoning = (
                f"LOW STOCK WARNING: Available units ({available_stock}) have fallen below the dynamic "
                f"reorder point ({dynamic_rop} units). Stock cover is {days_of_cover:.1f} days vs lead time {effective_lead_time}d."
            )
        elif days_of_cover > 90.0:
            # Over 90 days of inventory sitting idle ties up working capital
            stock_status = InventoryLevel.StockStatus.OVERSTOCKED
            is_overstocked = True
            reasoning = (
                f"OVERSTOCK DETECTED: Stock cover of {days_of_cover:.1f} days exceeds optimum 60-day threshold. "
                f"Capital tied up; replenishment holds recommended."
            )
        else:
            stock_status = InventoryLevel.StockStatus.OPTIMAL
            reasoning = (
                f"OPTIMAL BALANCE: Current stock cover of {days_of_cover:.1f} days comfortably covers "
                f"effective lead time of {effective_lead_time} days."
            )

        return InventoryHealthState(
            sku=inventory.product.sku,
            current_stock=inventory.current_stock,
            allocated_stock=inventory.allocated_stock,
            available_stock=available_stock,
            safety_stock=inventory.safety_stock,
            forecasted_daily_demand=daily_demand,
            days_of_stock_cover=days_of_cover,
            effective_lead_time_days=effective_lead_time,
            is_stockout_imminent=is_stockout_imminent,
            is_overstocked=is_overstocked,
            stock_status=stock_status,
            dynamic_rop=dynamic_rop,
            agent_reasoning=reasoning
        )


# ==============================================================================
# Agent 3: Planning Agent
# ==============================================================================
class PlanningAgent:
    """
    Strategic procurement decision maker.
    Synthesizes demand predictions, inventory health, supplier risks, and disruptions
    to formulate actionable Purchase Orders with comprehensive AI reasoning.
    """

    def formulate_procurement_plan(
        self,
        product: Product,
        inventory: InventoryLevel,
        demand: DemandState,
        inv_health: InventoryHealthState,
        active_disruptions: List[DisruptionAlert],
        candidate_suppliers: List[Supplier]
    ) -> ProcurementRecommendation:
        """
        Formulates PO draft or replenishment actions factoring MOQs, supplier reliability,
        and alternative vendor routing.
        """
        primary_supplier = inventory.primary_supplier

        # Evaluate if replenishment action is warranted
        needs_replenishment = (
            inv_health.stock_status in [
                InventoryLevel.StockStatus.CRITICAL_STOCKOUT,
                InventoryLevel.StockStatus.WARNING_LOW
            ]
        )

        if not needs_replenishment:
            return ProcurementRecommendation(
                sku=product.sku,
                supplier_id=str(primary_supplier.id) if primary_supplier else None,
                supplier_name=primary_supplier.name if primary_supplier else "None",
                action="HOLD",
                recommended_order_quantity=0,
                estimated_total_cost=Decimal("0.00"),
                urgency_level="LOW",
                ai_chain_of_thought=(
                    f"No procurement necessary for SKU {product.sku}. "
                    f"Days of Cover ({inv_health.days_of_stock_cover:.1f}d) exceeds the dynamic "
                    f"reorder point requirements. Preserving working capital."
                ),
                risk_summary="Inventory within safe operational boundaries.",
                alternative_supplier_recommended=False
            )

        # ------------------------------------------------------------------
        # Supplier Risk & Disruption Evaluation (Alternative Routing Check)
        # ------------------------------------------------------------------
        selected_supplier = primary_supplier
        switched_supplier = False
        alt_supplier_name = None
        risk_notes = []

        if active_disruptions:
            for alert in active_disruptions:
                risk_notes.append(f"Disruption [{alert.severity}]: {alert.headline} (+{alert.estimated_delay_days}d delay)")

        # If primary supplier risk score is elevated (> 0.40) or has active critical disruption,
        # evaluate candidate alternative suppliers
        primary_risk = primary_supplier.risk_score if primary_supplier else 0.50
        has_critical_disruption = any(d.severity in ['HIGH', 'CRITICAL'] for d in active_disruptions)

        if (primary_risk > 0.40 or has_critical_disruption) and candidate_suppliers:
            # Sort candidates by lowest risk score and lowest lead time
            viable_alts = [
                s for s in candidate_suppliers
                if s.is_active and (primary_supplier is None or s.id != primary_supplier.id)
            ]
            if viable_alts:
                # Pick the most reliable alternative
                best_alt = min(viable_alts, key=lambda s: (s.risk_score, s.lead_time_days))
                if best_alt.risk_score < primary_risk:
                    selected_supplier = best_alt
                    switched_supplier = True
                    alt_supplier_name = best_alt.name
                    risk_notes.append(
                        f"Autonomous Supplier Failover: Diverted procurement from primary supplier "
                        f"to '{best_alt.name}' due to high risk index ({primary_risk:.2f}) / disruption delays."
                    )

        # ------------------------------------------------------------------
        # Order Quantity Calculation (Economic Order / Coverage Target)
        # ------------------------------------------------------------------
        # Target: replenish inventory to cover 45 days of demand + safety stock
        target_cover_days = 45
        daily_demand = demand.forecasted_daily_demand
        moq = product.minimum_order_qty

        target_inventory_level = (daily_demand * target_cover_days) + inventory.safety_stock
        gross_needed = target_inventory_level - inv_health.available_stock
        
        # Enforce MOQ and batch rounding
        order_qty = max(moq, int(round(gross_needed)))
        # Round up to nearest multiple of 10 for standard packaging
        if order_qty % 10 != 0:
            order_qty = ((order_qty // 10) + 1) * 10

        unit_cost = product.unit_cost if product.unit_cost > Decimal('0.00') else Decimal('25.00')
        estimated_total = unit_cost * Decimal(order_qty)

        urgency = "CRITICAL" if inv_health.is_stockout_imminent else "HIGH"
        action = "EXPEDITE_PO" if inv_health.is_stockout_imminent else "DRAFT_PO"

        # ------------------------------------------------------------------
        # Multi-Agent Chain-of-Thought (CoT) Synthesis
        # ------------------------------------------------------------------
        cot_reasoning = (
            f"=== MULTI-AGENT PROCUREMENT REASONING ===\n"
            f"[Step 1: Demand Forecast]\n"
            f"  - Forecasted Daily Demand: {daily_demand:.2f} units/day (Trend: {demand.trend_category})\n"
            f"  - Demand Insight: {demand.agent_insights}\n\n"
            f"[Step 2: Inventory & Stock Cover Analysis]\n"
            f"  - Available Stock: {inv_health.available_stock} units\n"
            f"  - Days of Stock Cover: {inv_health.days_of_stock_cover:.1f} days\n"
            f"  - Dynamic Reorder Point: {inv_health.dynamic_rop} units (Baseline ROP: {product.baseline_rop})\n"
            f"  - Effective Lead Time: {inv_health.effective_lead_time_days} days\n"
            f"  - Stockout Imminent: {inv_health.is_stockout_imminent}\n\n"
            f"[Step 3: Supplier Risk & Routing]\n"
            f"  - Selected Vendor: {selected_supplier.name if selected_supplier else 'Unassigned'}\n"
            f"  - Supplier Risk Score: {selected_supplier.risk_score if selected_supplier else 'N/A'}\n"
            f"  - Active Disruptions Evaluated: {len(active_disruptions)}\n"
            f"  - Vendor Failover Triggered: {switched_supplier} (Alt: {alt_supplier_name})\n\n"
            f"[Step 4: Procurement Formulation]\n"
            f"  - Action Recommendation: {action}\n"
            f"  - Recommended Order Qty: {order_qty} units (enforcing MOQ {moq})\n"
            f"  - Estimated Capital Commitment: ${estimated_total:,.2f} (@ ${unit_cost}/unit)\n"
            f"  - Projected Stock Cover Post-Delivery: {target_cover_days} days"
        )

        return ProcurementRecommendation(
            sku=product.sku,
            supplier_id=str(selected_supplier.id) if selected_supplier else None,
            supplier_name=selected_supplier.name if selected_supplier else "Unassigned",
            action=action,
            recommended_order_quantity=order_qty,
            estimated_total_cost=estimated_total,
            urgency_level=urgency,
            ai_chain_of_thought=cot_reasoning,
            risk_summary="; ".join(risk_notes) if risk_notes else "Supplier operations standard.",
            alternative_supplier_recommended=switched_supplier,
            alternative_supplier_name=alt_supplier_name
        )


# ==============================================================================
# Multi-Agent Orchestrator Pipeline
# ==============================================================================
class MultiAgentSupplyChainOrchestrator:
    """
    Coordinates execution of Demand Agent -> Inventory Agent -> Planning Agent,
    persisting updated Days of Cover and autonomously drafting Purchase Orders.
    """

    def __init__(self):
        self.demand_agent = DemandAgent()
        self.inventory_agent = InventoryAgent()
        self.planning_agent = PlanningAgent()

    def run_replenishment_pipeline(
        self,
        product_sku: str,
        auto_draft_po: bool = True
    ) -> Dict[str, Any]:
        """
        Executes end-to-end cognitive loop for a single SKU.
        Updates InventoryLevel metrics in real-time.
        """
        product = Product.objects.get(sku=product_sku)
        inventory = getattr(product, 'inventory_level', None)

        if not inventory:
            # Initialize inventory record if absent
            inventory = InventoryLevel.objects.create(
                product=product,
                current_stock=0,
                safety_stock=20
            )

        # Retrieve active disruption alerts impacting this supplier or product
        active_disruptions = list(
            DisruptionAlert.objects.filter(
                is_resolved=False
            ).filter(
                affected_supplier=inventory.primary_supplier
            )
        )

        # -------------------------------------------------------------
        # Phase 1: Demand Agent Execution
        # -------------------------------------------------------------
        demand_state = self.demand_agent.analyze_demand(product=product)

        # -------------------------------------------------------------
        # Phase 2: Inventory Agent Execution
        # -------------------------------------------------------------
        inv_health = self.inventory_agent.evaluate_inventory_health(
            inventory=inventory,
            demand_state=demand_state,
            active_disruptions=active_disruptions
        )

        # Persist dynamic days of cover and recalculated dynamic ROP to DB
        inventory.days_of_stock_cover = Decimal(str(inv_health.days_of_stock_cover))
        inventory.dynamic_rop = inv_health.dynamic_rop
        inventory.stock_status = inv_health.stock_status
        inventory.save(update_fields=['days_of_stock_cover', 'dynamic_rop', 'stock_status', 'updated_at'])

        # -------------------------------------------------------------
        # Phase 3: Planning Agent Execution
        # -------------------------------------------------------------
        candidate_suppliers = list(Supplier.objects.filter(is_active=True))
        plan = self.planning_agent.formulate_procurement_plan(
            product=product,
            inventory=inventory,
            demand=demand_state,
            inv_health=inv_health,
            active_disruptions=active_disruptions,
            candidate_suppliers=candidate_suppliers
        )

        po_created = None
        if auto_draft_po and plan.action in ["DRAFT_PO", "EXPEDITE_PO"] and plan.recommended_order_quantity > 0:
            # Generate deterministic unique PO number
            supplier_obj = Supplier.objects.filter(id=plan.supplier_id).first() if plan.supplier_id else inventory.primary_supplier
            if supplier_obj:
                unique_suffix = f"{uuid.uuid4().hex[:6].upper()}-{product.sku[:6]}"
                po_number = f"PO-AI-{timezone.now().strftime('%Y%m%d%H%M%S')}-{unique_suffix}"
                po_created = PurchaseOrder.objects.create(
                    po_number=po_number,
                    supplier=supplier_obj,
                    product=product,
                    quantity=plan.recommended_order_quantity,
                    unit_cost=product.unit_cost,
                    total_cost=plan.estimated_total_cost,
                    status=PurchaseOrder.POStatus.PENDING_APPROVAL,
                    trigger_source=PurchaseOrder.TriggerSource.AI_AGENT,
                    ai_reasoning=plan.ai_chain_of_thought,
                    risk_assessment_summary=plan.risk_summary,
                )

        # Evaluate multi-echelon intra-network transfer feasibility
        from inventory_core.services.multi_echelon import MultiEchelonService
        transfer_recommendation = None
        if plan.action in ["DRAFT_PO", "EXPEDITE_PO"]:
            transfer_recommendation = MultiEchelonService.evaluate_inter_warehouse_transfer(
                product_sku=product.sku,
                required_units=plan.recommended_order_quantity
            )

        return {
            "sku": product.sku,
            "product_name": product.name,
            "demand_forecast": asdict(demand_state),
            "inventory_health": asdict(inv_health),
            "procurement_plan": asdict(plan),
            "stock_transfer_recommendation": transfer_recommendation,
            "purchase_order_drafted": {
                "po_number": po_created.po_number,
                "status": po_created.status,
                "quantity": po_created.quantity,
                "total_cost": float(po_created.total_cost),
                "ai_reasoning": po_created.ai_reasoning,
            } if po_created else None
        }
