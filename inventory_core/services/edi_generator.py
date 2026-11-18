"""
ANSI X12 EDI 850 Purchase Order Standard Generator & ERP Export Service.

Enterprise Feature:
Translates internal PurchaseOrder domain records into the globally recognized
ANSI X12 EDI 850 Purchase Order format required by major global retailers,
tier-1 manufacturers, and enterprise ERPs (SAP, Oracle SCM, Microsoft Dynamics, NetSuite).
"""

from datetime import datetime
from typing import Dict, Any, List
from inventory_core.models import PurchaseOrder


class EDIGeneratorService:
    """
    Generates industry standard EDI 850 transactions and ERP batch exports.
    """

    @classmethod
    def generate_edi_850(cls, po: PurchaseOrder) -> str:
        """
        Generates ANSI X12 EDI 850 format string for a purchase order.
        """
        now = datetime.now()
        date_str_yyyymmdd = now.strftime("%Y%m%d")
        date_str_yymmdd = now.strftime("%y%m%d")
        time_str_hhmm = now.strftime("%H%M")
        ctrl_num = f"{po.id.hex[:9].upper()}"

        buyer_id = "SUPPLYCHAINAI"
        supplier_id = po.supplier.name[:15].replace(" ", "").upper()
        po_number = po.po_number
        qty = po.quantity
        unit_price = f"{float(po.unit_cost):.2f}"
        total_cost = f"{float(po.total_cost):.2f}"
        sku = po.product.sku

        # Build standard X12 EDI 850 envelope & segments
        segments = [
            f"ISA*00*          *00*          *ZZ*{buyer_id:<15}*ZZ*{supplier_id:<15}*{date_str_yymmdd}*{time_str_hhmm}*U*00401*{ctrl_num}*0*P*>~",
            f"GS*PO*{buyer_id}*{supplier_id}*{date_str_yyyymmdd}*{time_str_hhmm}*1*X*004010~",
            f"ST*850*0001~",
            f"BEG*00*NE*{po_number}**{date_str_yyyymmdd}~",
            f"CUR*BY*USD~",
            f"REF*VR*{supplier_id}~",
            f"N1*BY*SUPPLY CHAIN AI CORP*92*001~",
            f"N1*SE*{po.supplier.name}*92*SUPP01~",
            f"PO1*1*{qty}*EA*{unit_price}*PE*BP*{sku}*VP*{sku}~",
            f"PID*F****{po.product.name}~",
            f"CTT*1*{qty}~",
            f"AMT*TT*{total_cost}~",
            f"SE*10*0001~",
            f"GE*1*1~",
            f"IEA*1*{ctrl_num}~",
        ]

        return "\n".join(segments)

    @classmethod
    def generate_erp_export_payload(cls, po: PurchaseOrder) -> Dict[str, Any]:
        """
        Generates structured JSON payload ready for direct webhook ingestion by ERPs.
        """
        return {
            "erp_transaction_type": "PURCHASE_ORDER_850",
            "po_number": po.po_number,
            "status": po.status,
            "supplier": {
                "id": str(po.supplier.id),
                "name": po.supplier.name,
                "region": po.supplier.region,
                "contact_email": po.supplier.contact_email,
            },
            "line_items": [
                {
                    "line_number": 1,
                    "product_sku": po.product.sku,
                    "product_name": po.product.name,
                    "quantity": po.quantity,
                    "unit_cost_usd": float(po.unit_cost),
                    "line_total_usd": float(po.total_cost),
                }
            ],
            "total_order_cost_usd": float(po.total_cost),
            "created_at": po.created_at.isoformat(),
            "ai_audit_reasoning": po.ai_reasoning,
            "edi_850_document": cls.generate_edi_850(po),
        }
