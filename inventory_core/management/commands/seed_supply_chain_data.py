"""
Management command to seed synthetic supply chain data.
Usage: python manage.py seed_supply_chain_data
"""

import os
from django.core.management.base import BaseCommand
from inventory_core.services.ingestion import PolarsDataIngestionService
from inventory_core.services.ai_agents import MultiAgentSupplyChainOrchestrator
from inventory_core.services.disruption_monitor import PredictiveDisruptionMonitor

class Command(BaseCommand):
    help = "Seeds synthetic suppliers, products, inventory, and sales history using Polars."

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        sample_dir = os.path.join(base_dir, "sample_data")

        self.stdout.write("1. Ingesting Suppliers with Polars...")
        res_s = PolarsDataIngestionService.ingest_suppliers_csv(os.path.join(sample_dir, "sample_suppliers.csv"))
        self.stdout.write(f"   Suppliers: {res_s}")

        self.stdout.write("2. Ingesting Products with Polars...")
        res_p = PolarsDataIngestionService.ingest_products_csv(os.path.join(sample_dir, "sample_products.csv"))
        self.stdout.write(f"   Products: {res_p}")

        self.stdout.write("3. Ingesting Inventory with Polars...")
        res_i = PolarsDataIngestionService.ingest_inventory_csv(os.path.join(sample_dir, "sample_inventory.csv"))
        self.stdout.write(f"   Inventory: {res_i}")

        self.stdout.write("4. Ingesting Sales History with Polars...")
        res_sh = PolarsDataIngestionService.ingest_sales_history_csv(os.path.join(sample_dir, "sample_sales_history.csv"))
        self.stdout.write(f"   Sales History: {res_sh}")

        self.stdout.write("5. Simulating Predictive Disruption News Feed...")
        alerts = PredictiveDisruptionMonitor.fetch_and_analyze_news()
        self.stdout.write(f"   Disruption Alerts Flagged: {len(alerts)}")

        self.stdout.write("6. Executing Multi-Agent Replenishment Pipeline for catalog...")
        from inventory_core.models import Product
        orchestrator = MultiAgentSupplyChainOrchestrator()
        for prod in Product.objects.all():
            r = orchestrator.run_replenishment_pipeline(prod.sku, auto_draft_po=True)
            po = r.get("purchase_order_drafted")
            if po:
                self.stdout.write(f"   [Drafted PO] SKU: {prod.sku} | Units: {po['quantity']} | Total: ${po['total_cost']:,.2f}")

        self.stdout.write(self.style.SUCCESS("Supply Chain database seeded and AI pipeline initialized successfully!"))
