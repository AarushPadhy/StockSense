"""
StockSense Natural Language AI Copilot Engine.

Competitive Uniqueness:
Traditional ERP suites (SAP, Netstock, Blue Yonder) require complex SQL queries,
custom report builders, or 20 clicks across dashboards.
The StockSense Copilot allows executives to query their real-time supply chain in
plain English and get instant answers with actionable telemetry and 1-click execution.
"""

from typing import Dict, Any, List
from decimal import Decimal
from django.db.models import Sum, Avg, Count
from inventory_core.models import Product, Supplier, InventoryLevel, PurchaseOrder, AutonomousActionLog, StockTransferRecommendation
from inventory_core.services.revenue_risk import RevenueRiskEngine
from inventory_core.services.ai_negotiator import AIVolumeDiscountArbitrageur


class StockSenseCopilot:
    """
    Interprets natural language queries, aggregates live telemetry, and returns executive answers.
    """

    @classmethod
    def ask(cls, user_prompt: str) -> Dict[str, Any]:
        prompt = user_prompt.lower().strip()

        # 1. Questions about stockouts or products running out
        if any(w in prompt for w in ["stockout", "run out", "empty", "critical", "danger", "urgent", "deplete"]):
            crit_items = InventoryLevel.objects.select_related('product', 'primary_supplier').filter(
                stock_status__in=['CRITICAL_STOCKOUT', 'WARNING_LOW']
            ).order_by('days_of_stock_cover')

            if not crit_items.exists():
                return {
                    "answer": "Great news! None of your products are at critical stockout risk right now. All inventory runways exceed supplier lead times.",
                    "intent": "INVENTORY_HEALTH_OPTIMAL",
                    "metrics": {"at_risk_count": 0},
                    "suggested_action": None
                }

            items_list = []
            for item in crit_items:
                items_list.append({
                    "sku": item.product.sku,
                    "name": item.product.name,
                    "days_of_cover": float(item.days_of_stock_cover),
                    "supplier_lead_time": item.primary_supplier.lead_time_days if item.primary_supplier else 14,
                    "units": item.current_stock
                })

            top_item = items_list[0]
            answer = (
                f"You have **{len(items_list)} products** requiring attention. "
                f"The most urgent is **{top_item['name']} ({top_item['sku']})**, with only **{top_item['days_of_cover']} days of stock left** "
                f"while supplier delivery takes {top_item['supplier_lead_time']} days. "
                f"Without replenishment, a stockout will occur within {top_item['days_of_cover']} days."
            )

            return {
                "answer": answer,
                "intent": "STOCKOUT_HAZARDS",
                "metrics": {
                    "at_risk_count": len(items_list),
                    "most_urgent_sku": top_item['sku'],
                    "items": items_list
                },
                "suggested_action": {
                    "label": f"Restock {top_item['sku']} with AI",
                    "action_type": "TRIGGER_REPLENISHMENT",
                    "sku": top_item['sku']
                }
            }

        # 2. Questions about money, capital, cash needed, spend
        elif any(w in prompt for w in ["cost", "capital", "cash", "money", "spend", "budget", "dollar", "how much"]):
            pos = PurchaseOrder.objects.filter(status__in=[PurchaseOrder.POStatus.PENDING_APPROVAL, PurchaseOrder.POStatus.DRAFT])
            total_pending = float(pos.aggregate(total=Sum('total_cost'))['total'] or 0.0)

            auto_spend = float(AutonomousActionLog.objects.aggregate(total=Sum('financial_impact_usd'))['total'] or 0.0)
            rev_risk = RevenueRiskEngine.evaluate_catalog_financial_exposure()
            lost_rev = rev_risk['summary']['total_revenue_at_risk_usd']

            answer = (
                f"Here is your financial capital breakdown:\n"
                f"• **Pending Purchase Orders:** ${total_pending:,.2f} awaiting approval or vendor payment.\n"
                f"• **Autonomous Auto-Pilot Spend to Date:** ${auto_spend:,.2f} safely executed under policy caps.\n"
                f"• **Potential Lost Revenue at Risk:** ${lost_rev:,.2f} across vulnerable catalog SKUs."
            )

            return {
                "answer": answer,
                "intent": "FINANCIAL_CAPITAL_INQUIRY",
                "metrics": {
                    "pending_po_value_usd": total_pending,
                    "total_automated_spend_usd": auto_spend,
                    "revenue_at_risk_usd": lost_rev
                },
                "suggested_action": {
                    "label": "Run Auto-Pilot Cycle",
                    "action_type": "RUN_CYCLE"
                }
            }

        # 3. Questions about suppliers, vendors, reliability
        elif any(w in prompt for w in ["supplier", "vendor", "partner", "factory", "slow", "delay", "reliability", "otif"]):
            suppliers = Supplier.objects.all().order_by('-lead_time_days')
            supp_list = []
            for s in suppliers:
                supp_list.append({
                    "name": s.name,
                    "region": s.region,
                    "lead_time": s.lead_time_days,
                    "risk_score": float(s.risk_score),
                    "reliability": "Tier 1 (High OTIF)" if s.risk_score < 0.25 else ("Tier 2" if s.risk_score < 0.55 else "High Risk")
                })

            worst = supp_list[0] if supp_list else None
            answer = (
                f"You have **{len(supp_list)} active suppliers** in your network. "
                + (f"**{worst['name']}** in {worst['region']} has the longest lead time ({worst['lead_time']} days) with a risk index of {worst['risk_score']:.2f}." if worst else "")
            )

            return {
                "answer": answer,
                "intent": "SUPPLIER_PERFORMANCE",
                "metrics": {"suppliers": supp_list},
                "suggested_action": {
                    "label": "Review Supplier Scorecards",
                    "action_type": "SWITCH_TAB",
                    "tab": "scorecards"
                }
            }

        # 4. Questions about Auto-Pilot, autonomous actions, what AI did
        elif any(w in prompt for w in ["autopilot", "auto-pilot", "automation", "audit", "history", "what did the ai do", "activity"]):
            logs = AutonomousActionLog.objects.order_by('-created_at')[:5]
            if not logs.exists():
                return {
                    "answer": "Auto-Pilot is active and monitoring your catalog. No orders have been executed yet today because inventory was safely above reorder points.",
                    "intent": "AUTONOMOUS_STATUS",
                    "metrics": {"actions_count": 0},
                    "suggested_action": {"label": "Run Cycle Now", "action_type": "RUN_CYCLE"}
                }

            lines = [f"• **{l.get_action_type_display()}**: {l.headline} (${float(l.financial_impact_usd):,.2f})" for l in logs]
            answer = (
                f"Here are the recent autonomous actions executed by StockSense:\n"
                + "\n".join(lines)
            )

            return {
                "answer": answer,
                "intent": "AUTONOMOUS_STATUS",
                "metrics": {"recent_actions": len(logs)},
                "suggested_action": {"label": "Run Cycle Now", "action_type": "RUN_CYCLE"}
            }

        # 5. Default intelligent assistant overview
        else:
            rev_data = RevenueRiskEngine.evaluate_catalog_financial_exposure()
            risk_skus = rev_data["summary"]["vulnerable_skus_count"]
            answer = (
                f"StockSense is actively defending your catalog of **{Product.objects.count()} products** across regional warehouses. "
                f"Currently, **{risk_skus} product(s)** require restock attention to protect ${rev_data['summary']['total_revenue_at_risk_usd']:,.2f} in potential sales. "
                f"You can ask me about stockout hazards, supplier reliability, cash requirements, or what Auto-Pilot executed!"
            )
            return {
                "answer": answer,
                "intent": "GENERAL_SUMMARY",
                "metrics": rev_data["summary"],
                "suggested_action": {"label": "Run Autonomous Sweep", "action_type": "RUN_CYCLE"}
            }
