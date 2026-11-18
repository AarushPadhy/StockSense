"""
StockSense Revenue at Risk & Ad-Spend Waste Shield Engine.

Competitive Uniqueness:
Legacy tools express stockout threats purely as operational unit shortages ("150 units short").
StockSense translates inventory deficits into direct executive financial impact:
1. Gross Margin & Lost Revenue at Risk ($)
2. Wasted Paid Acquisition / Ad Spend (Meta & Google ad spend burning on stockout landings)
3. Customer Lifetime Value (LTV) Churn Hazard
"""

from typing import Dict, Any, List
from decimal import Decimal
from inventory_core.models import Product, InventoryLevel, DisruptionAlert


class RevenueRiskEngine:
    """
    Computes financial exposure, lost margins, ad spend leakage, and customer churn from stockouts.
    """

    @classmethod
    def evaluate_catalog_financial_exposure(cls) -> Dict[str, Any]:
        products = Product.objects.select_related('inventory_level', 'inventory_level__primary_supplier').all()

        total_revenue_at_risk_usd = 0.0
        total_margin_at_risk_usd = 0.0
        total_wasted_ad_spend_usd = 0.0
        total_customer_ltv_loss_usd = 0.0
        vulnerable_skus_count = 0
        sku_risk_breakdowns = []

        for p in products:
            inv = getattr(p, 'inventory_level', None)
            if not inv:
                continue

            doc = float(inv.days_of_stock_cover)
            unit_price = float(p.unit_price)
            unit_cost = float(p.unit_cost)
            unit_margin = max(1.0, unit_price - unit_cost)

            # Daily demand estimation
            burn_rate = float(inv.current_stock) / max(1.0, doc) if doc > 0 else 5.0
            lead_time = inv.primary_supplier.lead_time_days if inv.primary_supplier else 14

            # If Days of Cover is less than supplier lead time, stockout days occur!
            deficit_days = max(0.0, float(lead_time) - doc)
            is_critical = doc <= 3.0 or deficit_days > 0

            if deficit_days > 0 or is_critical:
                vulnerable_skus_count += 1
                lost_units = round(burn_rate * deficit_days, 1)
                lost_revenue = round(lost_units * unit_price, 2)
                lost_margin = round(lost_units * unit_margin, 2)

                # Estimated ad spend burned during stockout period (~12% of lost top-line)
                wasted_ad_spend = round(lost_revenue * 0.12, 2)

                # Customer churn / LTV degradation (assuming 25% of unfulfilled customers defect)
                customer_ltv_loss = round(lost_revenue * 0.35, 2)

                total_revenue_at_risk_usd += lost_revenue
                total_margin_at_risk_usd += lost_margin
                total_wasted_ad_spend_usd += wasted_ad_spend
                total_customer_ltv_loss_usd += customer_ltv_loss

                sku_risk_breakdowns.append({
                    "sku": p.sku,
                    "name": p.name,
                    "days_of_cover": round(doc, 1),
                    "lead_time_days": lead_time,
                    "stockout_deficit_days": round(deficit_days, 1),
                    "burn_rate_daily": round(burn_rate, 1),
                    "units_short": int(lost_units),
                    "revenue_at_risk_usd": lost_revenue,
                    "margin_at_risk_usd": lost_margin,
                    "wasted_ad_spend_usd": wasted_ad_spend,
                    "customer_ltv_churn_usd": customer_ltv_loss,
                    "severity": "CRITICAL" if doc <= 2.0 else "HIGH",
                    "protective_action": "Execute Autonomous Transfer from West Coast Hub" if deficit_days < 7 else "Air-Freight Supplier Hedge PO"
                })

        # Sort by highest revenue at risk first
        sku_risk_breakdowns.sort(key=lambda x: x["revenue_at_risk_usd"], reverse=True)

        return {
            "summary": {
                "total_revenue_at_risk_usd": round(total_revenue_at_risk_usd, 2),
                "total_margin_at_risk_usd": round(total_margin_at_risk_usd, 2),
                "total_wasted_ad_spend_usd": round(total_wasted_ad_spend_usd, 2),
                "total_customer_ltv_loss_usd": round(total_customer_ltv_loss_usd, 2),
                "vulnerable_skus_count": vulnerable_skus_count,
                "total_catalog_skus": products.count(),
                "financial_health_score": max(20, int(100 - (vulnerable_skus_count * 12)))
            },
            "vulnerable_products": sku_risk_breakdowns
        }
