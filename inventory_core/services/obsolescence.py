"""
Inventory Obsolescence, Shelf-Life & Spoilage Monitor Service.

Enterprise Feature:
Evaluates remaining product shelf-life and technological obsolescence horizon against dynamic Days of Cover.
When Days of Cover exceeds remaining shelf life, unsold units risk becoming scrap.
Recommends dynamic clearance discounts or inter-warehouse redeployment.
"""

from decimal import Decimal
from typing import Dict, Any, List
from inventory_core.models import Product, InventoryLevel


# Default nominal lifecycle / shelf-life horizons (calendar days)
CATEGORY_SHELF_LIFE_DAYS = {
    "Materials": 180,       # Resins, adhesives, chemicals
    "Semiconductors": 365, # Rapid chip obsolescence
    "Sensors": 300,
    "Power Electronics": 365,
    "Optics": 450,
    "Networking": 365,
    "General": 360,
}


class ObsolescenceMonitorService:
    """
    Monitors capital at risk of expiration or technological depreciation.
    """

    @classmethod
    def evaluate_obsolescence_risk(cls, product: Product) -> Dict[str, Any]:
        """
        Compares dynamic Days of Cover against product shelf-life/lifecycle horizon.
        """
        inv = getattr(product, 'inventory_level', None)
        current_stock = inv.current_stock if inv else 0
        doc = float(inv.days_of_stock_cover) if inv else 0.0

        shelf_life_days = CATEGORY_SHELF_LIFE_DAYS.get(product.category, CATEGORY_SHELF_LIFE_DAYS["General"])

        # Surplus stock that will not be sold before shelf life expires:
        # daily_demand = current_stock / doc
        # consumable_before_expiration = daily_demand * shelf_life_days
        # expired_units = max(0, current_stock - consumable_before_expiration)
        is_obsolescence_hazard = doc > shelf_life_days

        daily_burn_rate = (current_stock / doc) if doc > 0 else 1.0
        consumable_units = int(round(daily_burn_rate * shelf_life_days))
        at_risk_units = max(0, current_stock - consumable_units)

        unit_cost = float(product.unit_cost if product.unit_cost > 0 else Decimal('25.00'))
        capital_at_risk_usd = round(at_risk_units * unit_cost, 2)

        # Strategic mitigation
        if is_obsolescence_hazard and at_risk_units > 0:
            status = "EXPIRATION_HAZARD"
            recommended_action = "PROMOTIONAL_MARKDOWN_OR_STOCK_TRANSFER"
            markdown_discount_pct = 20.0
            mitigation_note = (
                f"Surplus inventory ({at_risk_units} units, ${capital_at_risk_usd:,.2f}) will exceed "
                f"the {shelf_life_days}-day product lifecycle before organic sales can consume it. "
                f"Trigger a {int(markdown_discount_pct)}% clearance promotion or redeploy to high-velocity nodes."
            )
        elif doc > (shelf_life_days * 0.70):
            status = "OBSOLESCENCE_WARNING"
            recommended_action = "HALT_PROCUREMENT"
            markdown_discount_pct = 0.0
            mitigation_note = "Stock cover approaching 70% of lifecycle limit. Place temporary purchasing hold."
        else:
            status = "HEALTHY_ROTATION"
            recommended_action = "STANDARD_OPERATION"
            markdown_discount_pct = 0.0
            mitigation_note = "Inventory velocity comfortably within fresh lifecycle limits."

        return {
            "sku": product.sku,
            "product_name": product.name,
            "category": product.category,
            "current_stock": current_stock,
            "days_of_stock_cover": doc,
            "nominal_shelf_life_days": shelf_life_days,
            "obsolescence_status": status,
            "at_risk_units": at_risk_units,
            "capital_at_risk_usd": capital_at_risk_usd,
            "recommended_action": recommended_action,
            "recommended_markdown_discount_pct": markdown_discount_pct,
            "mitigation_guidance": mitigation_note,
        }

    @classmethod
    def scan_catalog_obsolescence(cls) -> Dict[str, Any]:
        """Scans catalog and aggregates total write-down exposure."""
        products = Product.objects.all()
        evaluations = [cls.evaluate_obsolescence_risk(p) for p in products]

        total_capital_at_risk = sum(e["capital_at_risk_usd"] for e in evaluations)
        hazard_items = [e for e in evaluations if e["obsolescence_status"] in ["EXPIRATION_HAZARD", "OBSOLESCENCE_WARNING"]]

        return {
            "total_capital_at_risk_usd": round(total_capital_at_risk, 2),
            "hazard_items_count": len(hazard_items),
            "total_catalog_items": len(products),
            "evaluations": evaluations
        }
