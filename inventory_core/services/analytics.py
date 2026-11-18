"""
Advanced Supply Chain Analytics & Competitive Intelligence Engine.

Synthesizes best-in-class features from global industry leaders:
1. Blue Yonder / Manhattan Associates: Dynamic ABC-XYZ Matrix Stratification.
2. Kinaxis RapidResponse / Anaplan: Digital Twin Resiliency Index (0-100 score).
3. Slimstock / ToolsGroup: Wilson Economic Order Quantity (EOQ) & Total Cost Optimization.
4. Resilinc / Everstream Analytics: Time-to-Survive (TTS) vs Time-to-Recover (TTR).
5. Flexport / Amazon Supply Chain: ESG Carbon Emissions Footprint (kg CO2e).
"""

import math
import numpy as np
from typing import Dict, Any, List
from decimal import Decimal
from django.utils import timezone

from inventory_core.models import (
    Product,
    Supplier,
    InventoryLevel,
    SalesHistory,
    DisruptionAlert,
    PurchaseOrder,
)
from inventory_core.services.forecasting import DemandForecaster


class SupplyChainAnalyticsService:
    """
    Computes enterprise-grade supply chain intelligence metrics.
    """

    # Standard annual carrying cost rate (20% of unit cost per year)
    ANNUAL_HOLDING_COST_RATE = 0.20
    # Average administrative and processing cost per purchase order placement ($USD)
    FIXED_ORDER_COST = 75.00

    @classmethod
    def calculate_abc_xyz_matrix(cls) -> Dict[str, Any]:
        """
        Classifies products into a 9-box ABC-XYZ matrix:
        - ABC (Volume/Revenue): A (top 70% value), B (next 20%), C (bottom 10%)
        - XYZ (Predictability): X (CV < 0.5, steady), Y (0.5 <= CV <= 1.0, variable), Z (CV > 1.0, erratic)
        """
        products = list(Product.objects.all())
        if not products:
            return {"matrix": {}, "summary": {}}

        product_metrics = []
        total_revenue_pool = 0.0

        for p in products:
            # Calculate annual run-rate revenue
            stats = DemandForecaster.analyze_product_demand(product=p, lookback_days=90)
            daily_demand = stats["forecasted_daily_demand"]
            annual_demand = daily_demand * 365.0
            unit_price = float(p.unit_price) if p.unit_price > 0 else float(p.unit_cost * Decimal('1.5'))
            annual_revenue = annual_demand * unit_price
            total_revenue_pool += annual_revenue

            # Coefficient of Variation (CV = std / mean) for XYZ
            mean_sales = stats["mean_daily_sales"]
            std_sales = stats["std_daily_sales"]
            cv = (std_sales / mean_sales) if mean_sales > 0 else 1.5

            product_metrics.append({
                "product": p,
                "annual_revenue": annual_revenue,
                "daily_demand": daily_demand,
                "cv": cv,
            })

        # Sort descending by annual revenue for Pareto ABC
        product_metrics.sort(key=lambda x: x["annual_revenue"], reverse=True)

        cumulative_rev = 0.0
        matrix_results = {
            "AX": [], "AY": [], "AZ": [],
            "BX": [], "BY": [], "BZ": [],
            "CX": [], "CY": [], "CZ": []
        }

        stratified_products = []

        for item in product_metrics:
            cumulative_rev += item["annual_revenue"]
            rev_share = (cumulative_rev / total_revenue_pool) if total_revenue_pool > 0 else 1.0

            # ABC Classification
            if rev_share <= 0.70:
                abc_class = "A"
            elif rev_share <= 0.90:
                abc_class = "B"
            else:
                abc_class = "C"

            # XYZ Classification
            cv = item["cv"]
            if cv < 0.50:
                xyz_class = "X"
            elif cv <= 1.00:
                xyz_class = "Y"
            else:
                xyz_class = "Z"

            cell = f"{abc_class}{xyz_class}"

            # Tailored replenishment strategy
            if cell == "AX":
                strategy = "Just-in-Time (JIT) / Automated Continuous Replenishment"
            elif cell == "AY":
                strategy = "Dynamic Buffer Stock with Weekly Forecasting"
            elif cell == "AZ":
                strategy = "Dual-Sourcing & Elevated Safety Stock Buffer"
            elif cell in ["BX", "BY"]:
                strategy = "Standard Periodic Review (Bi-weekly EOQ)"
            elif cell == "BZ":
                strategy = "Safety Stock Hedging & Contract Flexibility"
            else:
                strategy = "Kanban / Order-on-Demand (Minimize Holding Capital)"

            data_entry = {
                "sku": item["product"].sku,
                "name": item["product"].name,
                "abc_class": abc_class,
                "xyz_class": xyz_class,
                "matrix_cell": cell,
                "annual_revenue_usd": round(item["annual_revenue"], 2),
                "demand_volatility_cv": round(cv, 2),
                "recommended_strategy": strategy
            }
            matrix_results[cell].append(data_entry)
            stratified_products.append(data_entry)

        return {
            "stratified_products": stratified_products,
            "matrix_counts": {k: len(v) for k, v in matrix_results.items()},
            "total_catalog_revenue_runrate_usd": round(total_revenue_pool, 2)
        }

    @classmethod
    def calculate_resilience_and_tts_ttr(cls) -> Dict[str, Any]:
        """
        Resilinc / Everstream Analytics Paradigm:
        - Time-to-Survive (TTS): Number of operating days the company can fulfill orders
          if a supplier facility is completely shut down.
        - Time-to-Recover (TTR): Days required to qualify, spin up, and ship from an alternate source.
        - Vulnerability Flag: If TTS < TTR, a single supplier shutdown causes an inevitable line-stop!
        """
        inventories = InventoryLevel.objects.select_related('product', 'primary_supplier').all()
        active_disruptions = DisruptionAlert.objects.filter(is_resolved=False)
        all_suppliers = list(Supplier.objects.filter(is_active=True))

        sku_vulnerabilities = []
        critical_vulnerability_count = 0

        for inv in inventories:
            p = inv.product
            supplier = inv.primary_supplier
            doc = float(inv.days_of_stock_cover)

            # TTS is basically current Days of Stock Cover (operating days remaining without inbound shipments)
            tts_days = doc

            # TTR calculation: Lead time of best qualified alternative supplier + switchover overhead (7 days)
            base_lead = supplier.lead_time_days if supplier else 14
            alt_suppliers = [s for s in all_suppliers if supplier is None or s.id != supplier.id]
            if alt_suppliers:
                best_alt = min(alt_suppliers, key=lambda s: s.lead_time_days)
                ttr_days = best_alt.lead_time_days + 7  # 7-day emergency onboarding buffer
                has_backup = True
                backup_vendor = best_alt.name
            else:
                ttr_days = base_lead * 2  # No alternative; prolonged recovery
                has_backup = False
                backup_vendor = "None (Single-Source Risk)"

            is_vulnerable = tts_days < ttr_days
            deficit_days = max(0.0, round(ttr_days - tts_days, 1))

            if is_vulnerable:
                critical_vulnerability_count += 1

            sku_vulnerabilities.append({
                "sku": p.sku,
                "product_name": p.name,
                "primary_supplier": supplier.name if supplier else "Unassigned",
                "tts_days": round(tts_days, 1),
                "ttr_days": ttr_days,
                "deficit_days": deficit_days,
                "has_backup_vendor": has_backup,
                "backup_vendor_name": backup_vendor,
                "is_vulnerable": is_vulnerable,
                "resilience_status": "HIGH_EXPOSURE" if is_vulnerable else "RESILIENT",
            })

        # Calculate overall Digital Twin Resiliency Score (0 - 100)
        from django.db.models import Avg
        total_items = max(1, len(inventories))
        safe_ratio = 1.0 - (critical_vulnerability_count / total_items)
        avg_doc_val = inventories.aggregate(a=Avg('days_of_stock_cover'))['a']
        avg_doc = float(avg_doc_val) if avg_doc_val is not None else 15.0

        # Penalties based on active disruptions and supplier risks
        disruption_penalty = min(30.0, active_disruptions.count() * 6.0)
        avg_supplier_risk = (
            sum(s.risk_score for s in all_suppliers) / max(1, len(all_suppliers))
        ) if all_suppliers else 0.20
        risk_penalty = avg_supplier_risk * 25.0

        raw_score = (safe_ratio * 70.0) + min(30.0, avg_doc * 0.8) - disruption_penalty - risk_penalty
        composite_resiliency_score = max(5, min(100, int(round(raw_score))))

        # Qualitative health label
        if composite_resiliency_score >= 80:
            health_label = "ROBUST_OPTIMAL"
            color_grade = "EMERALD"
        elif composite_resiliency_score >= 60:
            health_label = "MODERATE_EXPOSURE"
            color_grade = "AMBER"
        else:
            health_label = "CRITICAL_FRAGILITY"
            color_grade = "ROSE"

        return {
            "composite_resiliency_score": composite_resiliency_score,
            "resilience_health_label": health_label,
            "color_grade": color_grade,
            "critical_vulnerability_count": critical_vulnerability_count,
            "total_evaluated_skus": total_items,
            "sku_vulnerabilities": sku_vulnerabilities,
        }

    @classmethod
    def calculate_wilson_eoq_and_cost(cls, product: Product) -> Dict[str, Any]:
        """
        Slimstock / ToolsGroup Paradigm:
        Wilson Economic Order Quantity (EOQ):
        EOQ = sqrt( (2 * AnnualDemand * FixedOrderCost) / HoldingCostPerUnitYear )
        """
        stats = DemandForecaster.analyze_product_demand(product=product, lookback_days=90)
        daily_demand = max(0.1, stats["forecasted_daily_demand"])
        annual_demand = daily_demand * 365.0

        unit_cost = float(product.unit_cost if product.unit_cost > 0 else Decimal('20.00'))
        holding_cost_unit_year = unit_cost * cls.ANNUAL_HOLDING_COST_RATE

        if holding_cost_unit_year > 0:
            raw_eoq = math.sqrt((2.0 * annual_demand * cls.FIXED_ORDER_COST) / holding_cost_unit_year)
            eoq_units = int(round(raw_eoq))
        else:
            eoq_units = product.minimum_order_qty

        # Enforce MOQ and round to nearest 10
        recommended_eoq = max(product.minimum_order_qty, eoq_units)
        if recommended_eoq % 10 != 0:
            recommended_eoq = ((recommended_eoq // 10) + 1) * 10

        annual_orders_count = round(annual_demand / recommended_eoq, 1)
        annual_ordering_cost = annual_orders_count * cls.FIXED_ORDER_COST
        annual_holding_cost = (recommended_eoq / 2.0) * holding_cost_unit_year
        total_annual_inventory_cost = round(annual_ordering_cost + annual_holding_cost, 2)

        return {
            "sku": product.sku,
            "recommended_eoq_units": recommended_eoq,
            "annual_demand_projected": int(round(annual_demand)),
            "annual_orders_count": annual_orders_count,
            "annual_holding_cost_usd": round(annual_holding_cost, 2),
            "annual_ordering_cost_usd": round(annual_ordering_cost, 2),
            "total_annual_inventory_cost_usd": total_annual_inventory_cost,
        }

    @classmethod
    def calculate_esg_carbon_emissions(cls, supplier_region: str, order_quantity: int, unit_weight_kg: float = 0.5) -> Dict[str, Any]:
        """
        Flexport / Amazon Supply Chain Paradigm:
        Estimates carbon footprint (kg CO2e) for freight transportation.
        - Ocean Freight: ~0.015 kg CO2e per ton-km
        - Air Freight: ~0.500 kg CO2e per ton-km (30x higher emissions)
        - Road / Rail: ~0.080 kg CO2e per ton-km
        """
        total_weight_ton = (order_quantity * unit_weight_kg) / 1000.0

        # Estimated average shipping distance to central distribution hub
        if supplier_region == "APAC":
            distance_km = 11000.0
            ocean_co2 = total_weight_ton * distance_km * 0.015
            air_co2 = total_weight_ton * distance_km * 0.500
        elif supplier_region == "EMEA":
            distance_km = 6500.0
            ocean_co2 = total_weight_ton * distance_km * 0.018
            air_co2 = total_weight_ton * distance_km * 0.520
        else:
            distance_km = 1500.0
            ocean_co2 = total_weight_ton * distance_km * 0.060  # Road trucking proxy
            air_co2 = total_weight_ton * distance_km * 0.450

        # Default recommended green shipping mode
        return {
            "supplier_region": supplier_region,
            "total_weight_kg": round(order_quantity * unit_weight_kg, 1),
            "ocean_intermodal_co2_kg": round(ocean_co2, 2),
            "expedited_air_co2_kg": round(air_co2, 2),
            "carbon_reduction_potential_kg": round(max(0.0, air_co2 - ocean_co2), 2),
            "green_freight_recommendation": "OCEAN_INTERMODAL" if order_quantity >= 50 else "STANDARD_TRUCKING"
        }

