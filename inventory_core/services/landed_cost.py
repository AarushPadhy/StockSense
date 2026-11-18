"""
Total Landed Cost & Customs Tariff Optimization Service.

Enterprise Feature:
Computes true Total Landed Cost per unit across international supply corridors:
Base Cost + International Freight + Customs Tariffs + Cargo Insurance + Port Handling.
Reveals when nearby suppliers with higher nominal prices actually deliver cheaper landed costs!
"""

from decimal import Decimal
from typing import Dict, Any, List
from inventory_core.models import Product, Supplier


# Standard regional customs tariffs & freight schedules
REGIONAL_TARIFF_SCHEDULE = {
    "APAC": {"tariff_rate": 0.125, "freight_per_unit": 3.80, "port_handling_fee": 1.20},
    "EMEA": {"tariff_rate": 0.045, "freight_per_unit": 2.90, "port_handling_fee": 0.90},
    "NA":   {"tariff_rate": 0.000, "freight_per_unit": 1.10, "port_handling_fee": 0.30},
}


class LandedCostService:
    """
    Computes landed costs and cross-supplier total cost comparisons.
    """

    INSURANCE_RATE = 0.006  # 0.6% marine cargo insurance

    @classmethod
    def calculate_landed_cost(
        cls,
        product: Product,
        supplier: Supplier,
        order_quantity: int = 100
    ) -> Dict[str, Any]:
        """
        Calculates detailed itemized landed cost per unit and total order financial liability.
        """
        base_unit_cost = float(product.unit_cost if product.unit_cost > 0 else Decimal('25.00'))
        region = supplier.region.upper() if supplier.region else "APAC"
        schedule = REGIONAL_TARIFF_SCHEDULE.get(region, REGIONAL_TARIFF_SCHEDULE["APAC"])

        tariff_rate = schedule["tariff_rate"]
        freight_per_unit = schedule["freight_per_unit"]
        port_handling = schedule["port_handling_fee"]

        tariff_cost_per_unit = round(base_unit_cost * tariff_rate, 2)
        insurance_cost_per_unit = round(base_unit_cost * cls.INSURANCE_RATE, 2)
        total_landed_cost_per_unit = round(
            base_unit_cost + freight_per_unit + tariff_cost_per_unit + insurance_cost_per_unit + port_handling,
            2
        )

        total_landed_order_cost = round(total_landed_cost_per_unit * order_quantity, 2)
        total_nominal_order_cost = round(base_unit_cost * order_quantity, 2)
        logistics_markup_pct = round(
            ((total_landed_cost_per_unit - base_unit_cost) / base_unit_cost) * 100.0,
            1
        ) if base_unit_cost > 0 else 0.0

        return {
            "sku": product.sku,
            "product_name": product.name,
            "supplier_name": supplier.name,
            "supplier_region": region,
            "order_quantity": order_quantity,
            "cost_breakdown_per_unit": {
                "base_purchase_price": base_unit_cost,
                "freight_transport": freight_per_unit,
                "customs_import_tariff": tariff_cost_per_unit,
                "marine_cargo_insurance": insurance_cost_per_unit,
                "port_handling_terminal": port_handling,
                "total_landed_cost": total_landed_cost_per_unit,
            },
            "financial_totals": {
                "total_nominal_po_cost_usd": total_nominal_order_cost,
                "total_landed_liability_usd": total_landed_order_cost,
                "logistics_tariff_markup_percent": logistics_markup_pct,
            },
            "tariff_rate_applied": f"{int(tariff_rate * 100)}%",
        }

    @classmethod
    def compare_supplier_corridors(cls, product_sku: str, order_quantity: int = 100) -> Dict[str, Any]:
        """
        Compares landed cost between all available suppliers for an SKU.
        """
        product = Product.objects.get(sku=product_sku)
        suppliers = list(Supplier.objects.filter(is_active=True))

        comparisons = []
        for s in suppliers:
            c = cls.calculate_landed_cost(product, s, order_quantity)
            comparisons.append(c)

        comparisons.sort(key=lambda x: x["cost_breakdown_per_unit"]["total_landed_cost"])
        cheapest_corridor = comparisons[0] if comparisons else None

        return {
            "sku": product.sku,
            "product_name": product.name,
            "order_quantity": order_quantity,
            "cheapest_landed_option": {
                "supplier_name": cheapest_corridor["supplier_name"] if cheapest_corridor else None,
                "region": cheapest_corridor["supplier_region"] if cheapest_corridor else None,
                "total_landed_cost_per_unit": cheapest_corridor["cost_breakdown_per_unit"]["total_landed_cost"] if cheapest_corridor else None,
            },
            "all_corridor_comparisons": comparisons
        }
