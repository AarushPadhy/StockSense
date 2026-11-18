# Frontend Integration & REST API Specification Guide

This comprehensive reference is designed for frontend developers building modern single-page applications (React, Next.js, Vue, Angular, Svelte) or using the built-in Apple-designed dashboard on top of the **StockSense Autonomous Inventory Intelligence Platform**.

---

## 🌐 Base Configuration

- **API Base URL**: `http://localhost:8000/api/v1/`
- **Dashboard Telemetry**: `http://localhost:8000/api/v1/dashboard/replenishment/`
- **Headers**:
  ```http
  Content-Type: application/json
  Accept: application/json
  ```
- **CORS**: Enabled for all origins in development (`CORS_ALLOW_ALL_ORIGINS = True`).

---

## 📐 TypeScript Type Definitions

Save these definitions in `types/supplyChain.ts`:

```typescript
// ==============================================================================
// Domain Models
// ==============================================================================

export type StockStatus = 
  | 'OPTIMAL'
  | 'WARNING_LOW'
  | 'CRITICAL_STOCKOUT'
  | 'OVERSTOCKED';

export type POStatus = 
  | 'DRAFT'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'TRANSMITTED'
  | 'FULFILLED';

export type DisruptionSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface Product {
  id: string;
  sku: string;
  name: string;
  category: string;
  description: string;
  unit_cost: string;        // Decimal string, e.g. "4.50"
  unit_price: string;       // Decimal string, e.g. "12.00"
  baseline_rop: number;     // Legacy static Reorder Point
  minimum_order_qty: number;
  created_at: string;
  updated_at: string;
}

export interface Supplier {
  id: string;
  name: string;
  contact_email: string;
  region: string;           // "APAC" | "EMEA" | "NA"
  lead_time_days: number;
  risk_score: number;       // 0.00 to 1.00
  reliability_rating: number; // 0.00 to 1.00
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryLevel {
  id: string;
  product: Product;
  primary_supplier: Supplier | null;
  current_stock: number;
  allocated_stock: number;
  available_stock: number;
  safety_stock: number;
  days_of_stock_cover: string; // e.g. "8.40"
  dynamic_rop: number;
  stock_status: StockStatus;
  last_replenished_at: string | null;
  updated_at: string;
}

export interface PurchaseOrder {
  id: string;
  po_number: string;
  supplier: string;          // UUID
  supplier_name: string;
  product: string;           // UUID
  product_sku: string;
  product_name: string;
  quantity: number;
  unit_cost: string;
  total_cost: string;
  status: POStatus;
  trigger_source: 'AI_AGENT' | 'MANUAL' | 'SCHEDULED_BATCH';
  ai_reasoning: string;      // Full Chain-of-Thought markdown/text
  risk_assessment_summary: string;
  approved_by: string | null;
  approved_at: string | null;
  expected_delivery_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface DisruptionAlert {
  id: string;
  headline: string;
  source_name: string;
  source_url: string;
  affected_supplier: string | null;
  affected_supplier_name: string | null;
  affected_product: string | null;
  affected_product_sku: string | null;
  severity: DisruptionSeverity;
  estimated_delay_days: number;
  impact_analysis: string;
  is_resolved: boolean;
  published_at: string;
  created_at: string;
}

export interface Warehouse {
  id: string;
  code: string;
  name: string;
  location: string;
  region: string;
  capacity_units: number;
  is_active: boolean;
  created_at: string;
}

export interface StockTransferRecommendation {
  id: string;
  product: string;
  product_sku: string;
  source_warehouse: string;
  source_warehouse_code: string;
  target_warehouse: string;
  target_warehouse_code: string;
  quantity: number;
  estimated_transit_days: number;
  cost_savings_usd: string;
  ai_reasoning: string;
  status: 'RECOMMENDED' | 'APPROVED' | 'IN_TRANSIT' | 'COMPLETED' | 'CANCELLED';
  created_at: string;
  updated_at: string;
}

export interface SupplierScorecard {
  supplier_id: string;
  supplier_name: string;
  region: string;
  contract_lead_time_days: number;
  p95_expected_lead_time_days: number;
  lead_time_variance_sigma_days: number;
  otif_delivery_percentage: number;
  defect_rate_ppm: number;
  composite_risk_score: number;
  vendor_tier: 'TIER_1_PREFERRED' | 'TIER_2_STANDARD' | 'TIER_3_PROBATION';
  vendor_tier_label: string;
  sla_compliance_status: 'EXCELLENT' | 'COMPLIANT' | 'BREACH_WARNING';
  total_lifetime_purchase_orders: number;
  is_active: boolean;
}

export interface LandedCostBreakdown {
  sku: string;
  product_name: string;
  supplier_name: string;
  supplier_region: string;
  order_quantity: number;
  cost_breakdown_per_unit: {
    base_purchase_price: number;
    freight_transport: number;
    customs_import_tariff: number;
    marine_cargo_insurance: number;
    port_handling_terminal: number;
    total_landed_cost: number;
  };
  financial_totals: {
    total_nominal_po_cost_usd: number;
    total_landed_liability_usd: number;
    logistics_tariff_markup_percent: number;
  };
  tariff_rate_applied: string;
}

export interface BullwhipAnalysis {
  sku: string;
  product_name: string;
  bullwhip_ratio: number;
  severity: 'BALANCED_SYNCHRONIZED' | 'MODERATE_AMPLIFICATION' | 'SEVERE_DISTORTION';
  demand_mean: number;
  demand_variance: number;
  orders_mean: number;
  orders_variance: number;
  damping_factor_applied: number;
  unfiltered_order_qty: number;
  smoothed_order_qty: number;
  inventory_glut_avoided_units: number;
  interpretation: string;
}

export interface ObsolescenceReport {
  sku: string;
  product_name: string;
  category: string;
  current_stock: number;
  days_of_stock_cover: number;
  nominal_shelf_life_days: number;
  obsolescence_status: 'HEALTHY_ROTATION' | 'OBSOLESCENCE_WARNING' | 'EXPIRATION_HAZARD';
  at_risk_units: number;
  capital_at_risk_usd: number;
  recommended_action: string;
  recommended_markdown_discount_pct: number;
  mitigation_guidance: string;
}

export interface EDIPurchaseOrderExport {
  erp_transaction_type: 'PURCHASE_ORDER_850';
  po_number: string;
  status: string;
  supplier: {
    id: string;
    name: string;
    region: string;
    contact_email: string;
  };
  line_items: Array<{
    line_number: number;
    product_sku: string;
    product_name: string;
    quantity: number;
    unit_cost_usd: number;
    line_total_usd: number;
  }>;
  total_order_cost_usd: number;
  created_at: string;
  ai_audit_reasoning: string;
  edi_850_document: string; // ANSI X12 EDI text format
}

// ==============================================================================
// Multi-Agent Pipeline Schemas
// ==============================================================================

export interface DemandState {
  sku: string;
  product_name: string;
  mean_daily_sales: number;
  std_daily_sales: number;
  trend_slope: number;
  trend_category: 'EXPANDING_GROWTH' | 'CONTRACTING_DECAY' | 'STEADY_STABLE' | 'COLD_START_BASELINE';
  forecasted_daily_demand: number;
  forecast_horizon_days: number;
  confidence_interval_95: [number, number];
  agent_insights: string;
}

export interface InventoryHealthState {
  sku: string;
  current_stock: number;
  allocated_stock: number;
  available_stock: number;
  safety_stock: number;
  forecasted_daily_demand: number;
  days_of_stock_cover: number;
  effective_lead_time_days: number;
  is_stockout_imminent: boolean;
  is_overstocked: boolean;
  stock_status: StockStatus;
  dynamic_rop: number;
  agent_reasoning: string;
}

export interface ProcurementPlan {
  sku: string;
  supplier_id: string | null;
  supplier_name: string;
  action: 'DRAFT_PO' | 'EXPEDITE_PO' | 'HOLD';
  recommended_order_quantity: number;
  estimated_total_cost: string;
  urgency_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  ai_chain_of_thought: string;
  risk_summary: string;
  alternative_supplier_recommended: boolean;
  alternative_supplier_name?: string | null;
}

export interface MultiAgentOrchestrationResponse {
  sku: string;
  product_name: string;
  demand_forecast: DemandState;
  inventory_health: InventoryHealthState;
  procurement_plan: ProcurementPlan;
  stock_transfer_recommendation?: StockTransferRecommendation | null;
  purchase_order_drafted?: {
    po_number: string;
    status: POStatus;
    quantity: number;
    total_cost: number;
    ai_reasoning: string;
  } | null;
}

// ==============================================================================
// Dashboard & Simulation Schemas
// ==============================================================================

export interface DashboardTelemetry {
  summary_kpis: {
    total_tracked_skus: number;
    critical_stockouts: number;
    warning_low_stock: number;
    optimal_stock: number;
    overstocked: number;
    average_days_of_cover: number;
    pending_ai_purchase_orders: number;
    pending_procurement_value_usd: number;
    active_disruption_threats: number;
    cumulative_delay_days_flagged: number;
    digital_twin_resiliency_score: number; // 0 to 100
    resilience_health_label: string;       // "ROBUST_OPTIMAL" | "MODERATE_EXPOSURE" | "CRITICAL_FRAGILITY"
    color_grade: 'EMERALD' | 'AMBER' | 'ROSE';
    vulnerable_skus_count: number;
  };
  urgent_replenishment_queue: Array<{
    sku: string;
    product_name: string;
    current_stock: number;
    available_stock: number;
    days_of_stock_cover: number;
    dynamic_rop: number;
    stock_status: StockStatus;
    supplier_name: string;
    supplier_lead_time: number;
  }>;
  recent_ai_drafted_pos: PurchaseOrder[];
  generated_at: string;
}

export interface WhatIfSimulationRequest {
  product_sku: string;
  demand_surge_percent?: number;      // e.g. 30.0 for +30%
  lead_time_delay_days?: number;      // e.g. 14
  supplier_risk_spike?: number;       // e.g. 0.20
  target_service_level?: number;      // e.g. 0.95 (95%)
}

export interface WhatIfSimulationResult {
  sku: string;
  product_name: string;
  simulation_parameters: {
    demand_surge_percent: number;
    lead_time_delay_days: number;
    supplier_risk_spike: number;
    target_service_level: number;
  };
  baseline_metrics: {
    daily_demand: number;
    lead_time_days: number;
    days_of_stock_cover: number;
    reorder_point: number;
    safety_stock: number;
    supplier_risk_score: number;
  };
  stressed_metrics: {
    daily_demand: number;
    lead_time_days: number;
    days_of_stock_cover: number;
    reorder_point: number;
    optimal_safety_stock: number;     // Recalibrated with King's formula
    supplier_risk_score: number;
    days_to_stockout: number;
    projected_stockout_date: string;  // "YYYY-MM-DD"
    stockout_imminent: boolean;
    hazard_level: 'CRITICAL' | 'HIGH' | 'NORMAL';
  };
  hedging_recommendation: {
    recommended_order_quantity: number;
    estimated_capital_usd: number;
    action: string;
  };
  ai_chain_of_thought: string;
}
```

---

## 📡 Complete REST API Endpoint Reference

### 1. Telemetry Dashboard
- **Endpoint**: `GET /api/v1/dashboard/replenishment/`
- **Description**: Returns all executive KPIs, critical low-cover SKUs, and recent AI purchase orders. Use this to hydrate your main dashboard screen.
- **Response**: `200 OK` -> `DashboardTelemetry`

---

### 2. Autonomous Multi-Agent Action Trigger
- **Endpoint**: `POST /api/v1/replenishment/draft-po/`
- **Description**: Triggers the 3-agent cognitive sequence (Demand -> Inventory -> Planning). Dynamically recalculates Days of Cover and drafts a PO in `PENDING_APPROVAL` with Chain-of-Thought reasoning.
- **Request Body**:
  ```json
  {
    "product_sku": "SKU-ELEC-1001",
    "auto_draft_po": true,
    "async_execution": false
  }
  ```
- **Response**: `200 OK` -> `{ message: string, data: MultiAgentOrchestrationResponse }`

---

### 3. What-If Scenario Stress Testing
- **Endpoint**: `POST /api/v1/simulation/what-if/`
- **Description**: Runs non-destructive parametric simulation. Calculates King's formula safety stock and projected stockout dates under demand surges and logistics disruptions.
- **Request Body**:
  ```json
  {
    "product_sku": "SKU-ELEC-1001",
    "demand_surge_percent": 30.0,
    "lead_time_delay_days": 14,
    "supplier_risk_spike": 0.20,
    "target_service_level": 0.95
  }
  ```
- **Response**: `200 OK` -> `WhatIfSimulationResult`

---

### 4. Semantic Disruption Vector Search (pgvector)
- **Endpoint**: `GET /api/v1/disruptions/semantic-search/?query=port+strike+in+asia&top_k=5`
  *(Or `POST /api/v1/disruptions/semantic-search/` with `{ query: "...", top_k: 5 }`)*
- **Description**: Computes 1536d query embedding and ranks disruption records by cosine similarity.
- **Response**:
  ```json
  {
    "query": "port strike in asia",
    "count": 2,
    "matches": [
      {
        "alert_id": "97e68fa7-...",
        "headline": "Dockworkers Strike Paralyzes Major Ningbo-Zhoushan Port Terminals in APAC",
        "similarity_score": 0.8842,
        "severity": "CRITICAL",
        "affected_supplier": "Shenzhen MicroElectronics Ltd",
        "estimated_delay_days": 12,
        "impact_analysis": "=== PREDICTIVE AI RAG RISK ASSESSMENT ==="
      }
    ]
  }
  ```

---

### 5. Purchase Order Management
- **`GET /api/v1/purchase-orders/`**: Lists all POs (supports filter `?status=PENDING_APPROVAL`).
- **`GET /api/v1/purchase-orders/{id}/`**: Retrieves PO details with full `ai_reasoning`.
- **`POST /api/v1/purchase-orders/{id}/approve/`**: Approves the drafted PO.
  - **Body**: `{ "approved_by": "Supply Chain Director" }`
  - **Response**: `200 OK` with updated status `APPROVED`.
- **`POST /api/v1/purchase-orders/{id}/reject/`**: Rejects the draft PO.
  - **Body**: `{}`
  - **Response**: `200 OK` with updated status `REJECTED`.

---

### 6. Multi-Echelon Stock Transfers
- **`GET /api/v1/stock-transfers/`**: Lists internal warehouse transfer recommendations.
- **`POST /api/v1/stock-transfers/{id}/approve/`**: Approves an intra-company transfer.
- **`GET /api/v1/warehouses/`**: Lists distribution center nodes.

---

### 7. High-Speed CSV Ingestion (Polars)
- **Endpoint**: `POST /api/v1/ingestion/upload-csv/`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `file_type`: `"suppliers"` | `"products"` | `"inventory"` | `"sales"`
  - `file`: CSV file binary
  - `async_processing`: `false` (immediate) or `true` (Celery background worker)
- **Response**:
  ```json
  {
    "status": "SUCCESS",
    "entity": "SalesHistory",
    "created": 581,
    "skipped": 0,
    "total_processed": 581
  }
  ```

---

### 8. Advanced Competitive Analytics & Matrix Endpoints
- **`GET /api/v1/analytics/abc-xyz/`**: Blue Yonder / Manhattan 9-box stratification matrix with tailored replenishment policies.
- **`GET /api/v1/analytics/resilience-tts/`**: Resilinc-style Time-to-Survive (TTS) vs Time-to-Recover (TTR) vulnerability index.
- **`GET /api/v1/analytics/eoq/?sku=SKU-ELEC-1001`**: Slimstock Wilson EOQ & Flexport ESG green freight carbon emissions analysis.
- **`POST /api/v1/playbooks/execute/`**:
  - **Body**: `{ "playbook": "port_strike_failover" | "demand_surge_stress" | "catalog_auto_pilot" }`
  - **Response**: Triggers automated simulation/auto-pilot routine and returns structured results.

---

### 9. Enterprise Capabilities (Scorecards, Landed Cost, Bullwhip, Obsolescence & EDI 850)
- **`GET /api/v1/suppliers/scorecards/`**: Returns OTIF percentage, lead-time variance ($\sigma_L$), PPM defect rate, and tier classification (`TIER_1_PREFERRED`, `TIER_2_STANDARD`, `TIER_3_PROBATION`) across all vendors.
- **`GET /api/v1/suppliers/{id}/scorecard/`**: Specific vendor scorecard audit.
- **`GET /api/v1/analytics/landed-cost/?sku={sku}&quantity={qty}`**: Total Landed Cost calculator comparing Base Price + Freight + Customs Tariffs + Cargo Insurance + Port Fees across international corridors.
- **`GET /api/v1/analytics/bullwhip/?sku={sku}`**: Quantifies the Forrester Bullwhip Effect ratio and provides low-pass smoothed order quantities to prevent upstream phantom order amplification.
- **`GET /api/v1/analytics/obsolescence-risk/`**: Scans products where Days of Cover exceeds remaining shelf-life, computing capital write-down risk and recommended clearance discounts.
- **`GET /api/v1/purchase-orders/{id}/export-edi/`**: Generates ANSI X12 EDI 850 Purchase Order standard transaction and JSON ERP export bundle.
- **`POST /api/v1/purchase-orders/{id}/transmit/`**: Approves and transmits PO to the supplier, generating EDI 850 and logging the action.
- **`POST /api/v1/stock-transfers/{id}/execute/`**: Dispatches the stock transfer, debiting donor inventory and transitioning status to `IN_TRANSIT`.

---

### 10. Autonomous Auto-Pilot & Zero-Touch Execution Engine
- **`GET /api/v1/automation/status/`**:
  - Returns master policy state (`is_enabled`), financial guardrail ceilings (`max_auto_po_value_usd`), reliability limits, live queue counters, and recent action audit logs.
- **`POST /api/v1/automation/toggle/`**:
  - Updates policy settings.
  - **Body**:
    ```json
    {
      "is_enabled": true,
      "max_auto_po_value": 25000.0,
      "min_supplier_reliability": 0.85,
      "auto_execute_transfers": true,
      "auto_transmit_edi": true
    }
    ```
- **`POST /api/v1/automation/run-cycle/`**:
  - Triggers an immediate catalog-wide autonomous replenishment sweep.
  - Automatically executes internal transfers, auto-approves POs under budget ceilings, and transmits EDI 850.
  - **Body**: `{ "force": true }`
  - **Response**:
    ```json
    {
      "status": "COMPLETED",
      "cycle_timestamp": "2026-11-18T14:47:32Z",
      "total_products_scanned": 7,
      "total_actions_executed": 38,
      "total_cycle_spend_usd": 20821.0,
      "executed_purchase_orders_count": 6,
      "executed_transfers_count": 32,
      "held_for_human_review_count": 0
    }
    ```
- **`GET /api/v1/automation/audit-logs/?limit=20`**:
  - Immutable audit trail of zero-touch automated actions (`PO_TRANSMITTED`, `TRANSFER_DISPATCHED`, `GUARDRAIL_HELD`).

---

### 11. Next-Gen Unique AI Features
- **`POST /api/v1/ai/copilot/`**:
  - Plain English Natural Language AI Copilot query.
  - **Body**: `{ "query": "Which products will run out of stock first?" }`
  - **Response**:
    ```json
    {
      "answer": "You have 2 products requiring attention...",
      "intent": "STOCKOUT_HAZARDS",
      "metrics": { "at_risk_count": 2, "most_urgent_sku": "SKU-ELEC-1001" },
      "suggested_action": { "label": "Restock with AI", "action_type": "TRIGGER_REPLENISHMENT", "sku": "SKU-ELEC-1001" }
    }
    ```
- **`GET /api/v1/ai/revenue-at-risk/`**:
  - Evaluates financial exposure: top-line revenue at risk, lost gross margins, and wasted ad spend.
  - **Response**:
    ```json
    {
      "summary": {
        "total_revenue_at_risk_usd": 18450.0,
        "total_margin_at_risk_usd": 8900.0,
        "total_wasted_ad_spend_usd": 2214.0,
        "total_customer_ltv_loss_usd": 6457.5,
        "vulnerable_skus_count": 2,
        "financial_health_score": 76
      },
      "vulnerable_products": [...]
    }
    ```
- **`POST /api/v1/ai/negotiate/`**:
  - Evaluates tiered volume discount arbitrage and generates supplier negotiation letters.
  - **Body**: `{ "product_sku": "SKU-ELEC-1001", "planned_order_qty": 100 }`
  - **Response**:
    ```json
    {
      "sku": "SKU-ELEC-1001",
      "product_name": "Aura ANC Wireless Headphones",
      "tiers": [
        { "tier_name": "Standard Batch", "quantity": 100, "unit_price_usd": 24.50, "discount_percent": 0.0 },
        { "tier_name": "Volume Arbitrage", "quantity": 150, "unit_price_usd": 22.54, "discount_percent": 8.0, "net_arbitrage_gain_usd": 294.0 }
      ],
      "negotiation_email_subject": "StockSense Order Schedule & Volume Pricing Review",
      "negotiation_email_body": "Dear Account Team..."
    }
    ```


---

## 🎨 UI Component Architecture Recommendations

1. **Days of Stock Cover Progress Bar**:
   - `DoC <= Effective Lead Time`: Render in **Red / Rose** with pulsating warning badge (`CRITICAL_STOCKOUT`).
   - `DoC <= Dynamic ROP / Daily Demand`: Render in **Amber** (`WARNING_LOW`).
   - `DoC between Lead Time and 60 days`: Render in **Emerald** (`OPTIMAL`).
   - `DoC > 90 days`: Render in **Purple** (`OVERSTOCKED`).

2. **Chain-of-Thought (CoT) Reasoning Display**:
   - The `ai_reasoning` string contains structured markdown headings:
     - `[Step 1: Demand Forecast]`
     - `[Step 2: Inventory & Stock Cover Analysis]`
     - `[Step 3: Supplier Risk & Routing]`
     - `[Step 4: Procurement Formulation]`
   - Render inside a collapsible `<details>` accordion or modal with monospaced code blocks for audit clarity.

3. **What-If Scenario Sandbox**:
   - Provide range sliders for **Demand Surge** ($0\%$ to $+150\%$) and **Lead Time Delay** ($0$ to $60$ days).
   - Display a comparative bar chart showing **Baseline DoC vs Stressed DoC** and **Current SS vs King's SS**.
