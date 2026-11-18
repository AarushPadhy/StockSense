import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "supply_chain_ai.settings")
django.setup()

from django.test import Client
from inventory_core.models import PurchaseOrder, StockTransferRecommendation

c = Client()
endpoints = [
    ("GET", "/api/v1/dashboard/replenishment/", None),
    ("GET", "/api/v1/inventory/", None),
    ("GET", "/api/v1/automation/status/", None),
    ("POST", "/api/v1/automation/toggle/", {"is_enabled": True}),
    ("POST", "/api/v1/automation/run-cycle/", {"force": True}),
    ("GET", "/api/v1/automation/audit-logs/?limit=8", None),
    ("POST", "/api/v1/replenishment/draft-po/", {"product_sku": "SKU-ELEC-1001", "auto_draft_po": True}),
    ("POST", "/api/v1/simulation/what-if/", {"demand_surge_factor": 1.4, "lead_time_delay_days": 0}),
    ("GET", "/api/v1/analytics/abc-xyz/", None),
    ("GET", "/api/v1/analytics/resilience-tts/", None),
    ("GET", "/api/v1/analytics/landed-cost/?sku=SKU-ELEC-1001", None),
    ("GET", "/api/v1/suppliers/scorecards/", None),
    ("GET", "/api/v1/analytics/bullwhip/", None),
    ("GET", "/api/v1/analytics/obsolescence-risk/", None),
    ("GET", "/api/v1/analytics/eoq/?sku=SKU-COMM-5001", None),
    ("GET", "/api/v1/purchase-orders/", None),
    ("GET", "/api/v1/stock-transfers/", None),
    ("POST", "/api/v1/ai/copilot/", {"query": "Which products will run out first?"}),
    ("GET", "/api/v1/ai/revenue-at-risk/", None),
    ("POST", "/api/v1/ai/negotiate/", {"product_sku": "SKU-ELEC-1001", "planned_order_qty": 100}),
]

passed = 0
failed = 0

for method, url, data in endpoints:
    if method == "GET":
        r = c.get(url)
    else:
        r = c.post(url, data=json.dumps(data) if data else "{}", content_type="application/json")
    if 200 <= r.status_code < 300:
        print(f"[PASS] {method} {url} -> {r.status_code}")
        passed += 1
    else:
        print(f"[FAIL] {method} {url} -> {r.status_code}: {r.content[:150]}")
        failed += 1

po = PurchaseOrder.objects.first()
if po:
    r_edi = c.get(f"/api/v1/purchase-orders/{po.id}/export-edi/")
    if r_edi.status_code == 200:
        print(f"[PASS] GET /api/v1/purchase-orders/{po.id}/export-edi/ -> 200")
        passed += 1
    else:
        print(f"[FAIL] GET /api/v1/purchase-orders/{po.id}/export-edi/ -> {r_edi.status_code}")
        failed += 1

    r_tx = c.post(f"/api/v1/purchase-orders/{po.id}/transmit/")
    if r_tx.status_code == 200:
        print(f"[PASS] POST /api/v1/purchase-orders/{po.id}/transmit/ -> 200")
        passed += 1
    else:
        print(f"[FAIL] POST /api/v1/purchase-orders/{po.id}/transmit/ -> {r_tx.status_code}")
        failed += 1

tr = StockTransferRecommendation.objects.first()
if tr:
    r_tr = c.post(f"/api/v1/stock-transfers/{tr.id}/execute/")
    if r_tr.status_code == 200:
        print(f"[PASS] POST /api/v1/stock-transfers/{tr.id}/execute/ -> 200")
        passed += 1
    else:
        print(f"[FAIL] POST /api/v1/stock-transfers/{tr.id}/execute/ -> {r_tr.status_code}")
        failed += 1

print(f"\n==========================================")
print(f"VERIFICATION SUMMARY: {passed} PASSED, {failed} FAILED")
print(f"==========================================")
