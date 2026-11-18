"""
Supply Chain What-If Scenario Simulation & Stress-Testing Engine.

Architectural Design:
Allows supply chain operators and planners to execute non-destructive stress tests:
- Demand surge shocks (e.g., +30% promo or viral surge)
- Supply chain logistics delays (e.g., +14 days port blockage)
- Supplier risk index spikes
- Service-level adjustments (90%, 95%, 98%, 99%)
Calculates dynamic King-formula safety stock, projected stock-out dates, and hedge recommendations.
"""

import math
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone

from inventory_core.models import Product, Supplier, InventoryLevel, DisruptionAlert
from inventory_core.services.forecasting import DemandForecaster


# Standard normal distribution Z-scores for target cycle service levels
Z_SCORE_MAP = {
    0.90: 1.282,
    0.95: 1.645,
    0.98: 2.054,
    0.99: 2.326,
}


class SupplyChainSimulator:
    """
    Executes parametric stress-testing and simulation against SKU inventory.
    """

    @classmethod
    def run_what_if_scenario(
        cls,
        product_sku: str,
        demand_surge_percent: float = 0.0,
        lead_time_delay_days: int = 0,
        supplier_risk_spike: float = 0.0,
        target_service_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Runs a simulation scenario comparing baseline versus shocked operational reality.
        """
        product = Product.objects.get(sku=product_sku)
        inv = getattr(product, 'inventory_level', None)
        supplier = inv.primary_supplier if inv else None

        current_stock = inv.current_stock if inv else 0
        allocated_stock = inv.allocated_stock if inv else 0
        available_stock = max(0, current_stock - allocated_stock)
        current_safety_stock = inv.safety_stock if inv else 20

        # Baseline empirical forecast
        base_stats = DemandForecaster.analyze_product_demand(product=product, lookback_days=90, forecast_horizon_days=14)
        base_daily_demand = max(0.1, base_stats["forecasted_daily_demand"])
        base_lead_time = supplier.lead_time_days if supplier else 14
        base_risk_score = supplier.risk_score if supplier else 0.15

        # Baseline Days of Cover
        base_doc = round(available_stock / base_daily_demand, 2)
        base_rop = int(round((base_daily_demand * base_lead_time) + current_safety_stock))

        # -------------------------------------------------------------
        # Apply Scenario Stressors
        # -------------------------------------------------------------
        surge_multiplier = 1.0 + (demand_surge_percent / 100.0)
        stressed_daily_demand = max(0.1, base_daily_demand * surge_multiplier)
        stressed_lead_time = max(1, base_lead_time + lead_time_delay_days)
        stressed_risk_score = min(1.0, max(0.0, base_risk_score + supplier_risk_spike))

        # Stressed Days of Cover
        stressed_doc = round(available_stock / stressed_daily_demand, 2)

        # -------------------------------------------------------------
        # Dynamic Safety Stock Optimization (King's Formula)
        # SS = Z * sqrt( L * (sigma_D^2) + (D_avg^2) * (sigma_L^2) )
        # -------------------------------------------------------------
        z_factor = Z_SCORE_MAP.get(target_service_level, 1.645)
        sigma_d = max(0.5, base_stats.get("std_daily_sales", 1.0) * surge_multiplier)
        # Estimate lead time standard deviation (~20% of lead time + delay uncertainty)
        sigma_l = max(1.0, stressed_lead_time * 0.20 + (lead_time_delay_days * 0.15))

        variance_term = (stressed_lead_time * (sigma_d ** 2)) + ((stressed_daily_demand ** 2) * (sigma_l ** 2))
        optimal_safety_stock = int(round(z_factor * math.sqrt(variance_term)))

        # Stressed Dynamic ROP
        stressed_rop = int(round((stressed_daily_demand * stressed_lead_time) + optimal_safety_stock))

        # Projected Stockout Date
        days_to_stockout = stressed_doc
        projected_stockout_date = (timezone.now() + timedelta(days=days_to_stockout)).strftime('%Y-%m-%d')

        # Stockout Hazard Evaluation
        stockout_imminent = days_to_stockout <= stressed_lead_time
        stockout_severity = "CRITICAL" if days_to_stockout < 5 else ("HIGH" if stockout_imminent else "NORMAL")

        # Recommended Hedge Quantity
        target_horizon_days = 45
        recommended_buffer_units = int(round(
            max(product.minimum_order_qty, (stressed_daily_demand * target_horizon_days) + optimal_safety_stock - available_stock)
        ))
        if recommended_buffer_units % 10 != 0:
            recommended_buffer_units = ((recommended_buffer_units // 10) + 1) * 10

        unit_cost = float(product.unit_cost if product.unit_cost > Decimal('0.00') else Decimal('25.00'))
        estimated_hedge_cost = round(recommended_buffer_units * unit_cost, 2)

        # AI Chain-of-Thought Scenario Narrative
        scenario_narrative = (
            f"=== WHAT-IF SCENARIO STRESS TEST ANALYSIS ===\n"
            f"Target: SKU {product.sku} ({product.name})\n"
            f"Applied Stressors:\n"
            f"  - Demand Shock: +{demand_surge_percent:.1f}% ({base_daily_demand:.1f} -> {stressed_daily_demand:.1f} units/day)\n"
            f"  - Lead Time Disruption: +{lead_time_delay_days} days ({base_lead_time} -> {stressed_lead_time} days)\n"
            f"  - Supplier Risk Escalation: +{supplier_risk_spike:.2f} ({base_risk_score:.2f} -> {stressed_risk_score:.2f})\n\n"
            f"Impact Assessment:\n"
            f"  - Days of Cover Depleted from {base_doc} days down to {stressed_doc} days.\n"
            f"  - Projected Stockout Date: {projected_stockout_date} (in {days_to_stockout:.1f} days).\n"
            f"  - Imminent Stockout Hazard: {stockout_imminent} (Status: {stockout_severity}).\n"
            f"  - Safety Stock Recalibration (King Formula @ {int(target_service_level*100)}% SL): "
            f"Dynamic SS increased from {current_safety_stock} to {optimal_safety_stock} units.\n"
            f"  - Dynamic Reorder Point escalated from {base_rop} to {stressed_rop} units.\n\n"
            f"Recommended Mitigating Action:\n"
            f"  - Autonomously hedge by expediting a purchase order of {recommended_buffer_units} units "
            f"totaling ${estimated_hedge_cost:,.2f}."
        )

        return {
            "sku": product.sku,
            "product_name": product.name,
            "simulation_parameters": {
                "demand_surge_percent": demand_surge_percent,
                "lead_time_delay_days": lead_time_delay_days,
                "supplier_risk_spike": supplier_risk_spike,
                "target_service_level": target_service_level,
            },
            "baseline_metrics": {
                "daily_demand": base_daily_demand,
                "lead_time_days": base_lead_time,
                "days_of_stock_cover": base_doc,
                "reorder_point": base_rop,
                "safety_stock": current_safety_stock,
                "supplier_risk_score": base_risk_score,
            },
            "stressed_metrics": {
                "daily_demand": round(stressed_daily_demand, 2),
                "lead_time_days": stressed_lead_time,
                "days_of_stock_cover": stressed_doc,
                "reorder_point": stressed_rop,
                "optimal_safety_stock": optimal_safety_stock,
                "supplier_risk_score": round(stressed_risk_score, 2),
                "days_to_stockout": round(days_to_stockout, 1),
                "projected_stockout_date": projected_stockout_date,
                "stockout_imminent": stockout_imminent,
                "hazard_level": stockout_severity,
            },
            "hedging_recommendation": {
                "recommended_order_quantity": recommended_buffer_units,
                "estimated_capital_usd": estimated_hedge_cost,
                "action": "EXPEDITE_HEDGE_PO" if stockout_imminent else "ADJUST_SAFETY_STOCK",
            },
            "ai_chain_of_thought": scenario_narrative,
        }
