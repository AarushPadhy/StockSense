# StockSense — Application Architecture & In-Depth Operation Manual

---

## 1. Executive Summary & Philosophy

**StockSense** is an autonomous inventory intelligence and supply chain optimization platform. Traditional inventory management systems rely on rigid, static Reorder Points (ROP) that inevitably fail during sudden demand spikes, shipping congestion, or geopolitical disruptions. 

StockSense replaces manual spreadsheets and static rules with a continuous, closed-loop multi-agent cognitive architecture:
1. **Dynamic Days of Cover (DoC)** replaces static min/max thresholds.
2. **Multi-Agent Collaborative Intelligence** (Demand Agent, Inventory Health Agent, Planning Agent) reasons through replenishment decisions in plain English.
3. **Autonomous Auto-Pilot Execution** transmits approved Purchase Orders via enterprise ANSI X12 EDI 850 protocols and balances regional warehouse inventory via inter-hub transfers.
4. **Apple-Grade Executive Interface** gives business owners immediate clarity without cognitive clutter, while preserving deep technical telemetry for analysts.

---

## 2. System Architecture & End-to-End Data Flow

```mermaid
flowchart TD
    subgraph DataIngestion ["1. High-Speed Data Ingestion"]
        CSV[CSV / ERP Feeds] --> Polars[Polars Ingestion Engine]
        Polars --> DB[(PostgreSQL / TimescaleDB)]
        News[Global Disruption Feeds] --> PgVector[(pgvector 1536d Embeddings)]
    end

    subgraph MultiAgentEngine ["2. Multi-Agent Replenishment Pipeline"]
        DB --> DA[Demand Forecasting Agent]
        DB --> IA[Inventory Health & Buffer Agent]
        PgVector --> IA
        DA --> PA[Planning & Sourcing Agent]
        IA --> PA
        PA --> Decision[Procurement Plan & CoT Explanation]
    end

    subgraph AutoPilotExecution ["3. Autonomous Auto-Pilot Subsystem"]
        Decision --> PolicyCheck{AutoPilotPolicy Guardrails}
        PolicyCheck -- Within Ceiling -- --> AutoApprove[Autonomous Execution Engine]
        PolicyCheck -- Above Ceiling -- --> ManualQueue[Pending Executive Review]
        AutoApprove --> EDI[ANSI X12 EDI 850 Generator]
        AutoApprove --> Transfers[Multi-Hub Stock Transfers]
        AutoApprove --> AuditLog[AutonomousActionLog Immutable Audit]
    end

    subgraph PresentationLayer ["4. Apple-Grade Executive Interface"]
        AuditLog --> UI[StockSense Command Center]
        EDI --> UI
        ManualQueue --> UI
        UI --> ExecMode[Executive Simple Overview]
        UI --> DeepDive[9 Technical Analyst Modules]
    end
```

---

## 3. The Multi-Agent Cognitive Architecture

The replenishment pipeline executes three collaborative agents for every tracked SKU:

### 3.1. Demand Forecasting Agent (`DemandForecaster`)
- **Input**: 90-day historical sales transaction stream.
- **Computation**:
  - Daily sales average: $\bar{d} = \frac{1}{N}\sum_{i=1}^N d_i$
  - Demand variance ($\sigma_d$) and standard deviation.
  - Linear velocity trend factor ($\beta$) via empirical regression.
- **Output**: Forecasted daily burn rate and forecast volatility index.

### 3.2. Inventory Health & Resilience Agent (`King's Dynamic Safety Stock`)
- **Input**: On-hand units, allocated units, supplier contract lead time ($L$), lead-time variance ($\sigma_L$), and active geopolitical disruption delay flags ($\Delta L$).
- **Effective Lead Time**:
  $$L_{\text{effective}} = L + \Delta L$$
- **Dynamic Days of Cover (DoC)**:
  $$\text{DoC} = \frac{\text{Current Stock} - \text{Allocated Stock}}{\text{Forecasted Daily Demand}}$$
- **King's Formula Dynamic Safety Stock ($SS$)**:
  $$SS = Z \cdot \sqrt{L_{\text{effective}} \cdot \sigma_d^2 + \bar{d}^2 \cdot \sigma_L^2}$$
  *(where $Z = 1.645$ for 95% cycle service level, or $2.054$ for 98%)*
- **Dynamic Reorder Point ($ROP$)**:
  $$ROP = (\bar{d} \cdot L_{\text{effective}}) + SS$$

### 3.3. Planning & Procurement Agent (`MultiAgentSupplyChainOrchestrator`)
- Evaluates primary and secondary vendor contracts, Minimum Order Quantities (MOQ), volume tier pricing breaks, and corridor risk indices.
- If current stock $\le ROP$, generates a precise replenishment quantity:
  $$Q = \max(\text{MOQ}, \lceil ROP - \text{Current Stock} + (\bar{d} \cdot \text{Target Cover Days}) \rceil)$$
- Synthesizes a human-readable **Chain-of-Thought (CoT)** reasoning narrative explaining *why* the order is needed and *which* supplier was selected.

---

## 4. Autonomous Auto-Pilot Subsystem

The Auto-Pilot engine enables hands-free supply chain operations within safe business guardrails:

### 4.1. Guardrails & Configuration (`AutoPilotPolicy`)
- `is_enabled`: Master power switch (Active vs. Paused).
- `max_auto_po_value_usd`: Financial ceiling per single purchase order (e.g., $15,000). Any order exceeding this limit is held in `PENDING_APPROVAL` for manual executive sign-off.
- `auto_approve_po`: Permission flag to approve qualified purchase orders autonomously.
- `auto_dispatch_transfers`: Permission flag to balance inter-warehouse stock across regional hubs.
- `require_trusted_supplier_only`: Restricts automatic PO transmission to Tier-1 vendors with OTIF delivery records $>90\%$.

### 4.2. ANSI X12 EDI 850 Transaction Generation
When an order is approved, StockSense compiles a standard ANSI X12 EDI 850 Purchase Order envelope for ERP and supplier network transmission:
```edi
ISA*00*          *00*          *ZZ*STOCKSENSE     *01*SUPPLIER01     *261118*2100*U*00401*000000001*0*P*>~
GS*PO*STOCKSENSE*SUPPLIER01*20261118*2100*1*X*004010~
ST*850*0001~
BEG*00*NE*PO-AI-20261118-001**20261118~
REF*IA*VENDOR-ACCT-4491~
PO1*1*500*EA*24.50**VN*SKU-ELEC-1001*BP*SKU-ELEC-1001~
PID*F****Aura ANC Wireless Headphones~
CTT*1~
SE*8*0001~
GE*1*1~
IEA*1*000000001~
```

### 4.3. Multi-Hub Intra-Network Stock Transfers
Rather than paying rush air-freight fees to overseas suppliers when a regional hub runs low, StockSense evaluates surplus stock at nearby company warehouses and dispatches low-cost ground freight transfers, saving up to 85% in logistics expenses.

---

## 5. Technical Deep Dive Analytical Engines

For supply chain directors and analysts, StockSense provides 9 advanced modules:

| # | Analytical Engine | Standard / Method | Business Value |
|---|-------------------|-------------------|----------------|
| 1 | **ABC-XYZ Matrix** | Revenue Volume $\times$ Demand Volatility (9-box) | Maps catalog items to tailored replenishment policies (Just-in-Time, Kanban, or Safety Buffer). |
| 2 | **Resilience TTS vs. TTR** | Resilinc / Everstream Digital Twin metric | Compares Time-to-Survive (TTS) against supplier Time-to-Recover (TTR) to identify shutdown deficits. |
| 3 | **Delivered Landed Cost** | Multi-corridor customs, tariffs, insurance & freight | Calculates delivered per-unit cost across global trade lanes to optimize sourcing margins. |
| 4 | **Supplier Scorecards** | OTIF (On-Time In-Full), $\sigma_L$, Defect PPM | Classifies suppliers into Tier 1, Tier 2, and High-Risk tiers with SLA compliance monitoring. |
| 5 | **Bullwhip Suppression** | Forrester ratio $\frac{\sigma_{\text{orders}}^2 / \mu_{\text{orders}}}{\sigma_{\text{demand}}^2 / \mu_{\text{demand}}}$ | Applies low-pass damping filters to order signals to avoid artificial bullwhip inventory gluts. |
| 6 | **Obsolescence Defense** | Shelf-life remaining vs. Days of Cover | Flags expired or superseded stock to trigger markdown liquidation before write-down. |
| 7 | **Wilson EOQ Lot Sizing** | $\sqrt{\frac{2 \cdot D \cdot S}{H}}$ batch economics | Identifies the order lot size that minimizes the sum of holding costs and order placement fees. |
| 8 | **Flexport ESG Green Freight** | GLEC Framework Intermodal CO$_2$ calculation | Compares ocean intermodal emissions vs. expedited air freight to reduce carbon footprints. |
| 9 | **Multi-Hub Balancing** | Network linear cost optimization | Reallocates surplus warehouse stock to donor hubs before ordering new factory batches. |

---

## 6. Apple Design System & Frontend Architecture

The user interface of StockSense is built using Apple's "Pro" dark-mode aesthetics:
- **Canvas**: True pitch-black `#000000` with high-contrast optical hierarchy.
- **Materials**: Multi-layered frosted glass (`backdrop-filter: blur(28px)`) with hairline specular highlights (`rgba(255, 255, 255, 0.08)`).
- **Typography**: San Francisco (`-apple-system`, `SF Pro Display`, `SF Pro Text`, `SF Mono`).
- **Interactive Physics**: Cubic-bezier fluid transitions (`cubic-bezier(0.16, 1, 0.3, 1)`) with `active:scale-[0.97]` tactile click feedback.
- **Dual Perspective Modes**:
  - **Executive (Simple)**: Plain-English summaries, runway countdowns, live health indices, and 1-click replenishment.
  - **Deep Dive (Analyst)**: Detailed data matrices, Wilson EOQ batches, EDI transaction inspectors, and OTIF compliance.

---

## 7. Verified REST API Reference

All 20 endpoints are active and verified:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboard/replenishment/` | Executive telemetry KPIs & digital twin resilience score |
| `GET` | `/api/v1/inventory/` | Product catalog with stock levels, DoC, and vendor lead times |
| `GET` | `/api/v1/automation/status/` | Auto-Pilot status, policy ceilings, and spend telemetry |
| `POST` | `/api/v1/automation/toggle/` | Enable/pause Auto-Pilot and update PO value limits |
| `POST` | `/api/v1/automation/run-cycle/` | Manually trigger a full autonomous scanning & execution cycle |
| `GET` | `/api/v1/automation/audit-logs/?limit=8` | Immutable audit trail of autonomous actions |
| `POST` | `/api/v1/replenishment/draft-po/` | Multi-agent replenishment calculation and PO draft |
| `POST` | `/api/v1/simulation/what-if/` | Parametric stress testing (demand spikes, port delays) |
| `GET` | `/api/v1/analytics/abc-xyz/` | 9-box catalog classification matrix |
| `GET` | `/api/v1/analytics/resilience-tts/` | Time-to-Survive vs. Time-to-Recover resilience index |
| `GET` | `/api/v1/analytics/landed-cost/?sku=<SKU>` | Global corridor delivered landed cost & tariffs |
| `GET` | `/api/v1/suppliers/scorecards/` | Supplier OTIF delivery rates and defect PPM |
| `GET` | `/api/v1/analytics/bullwhip/` | Forrester bullwhip ratios and smoothed order quantities |
| `GET` | `/api/v1/analytics/obsolescence-risk/` | Working capital at risk from expiry and obsolescence |
| `GET` | `/api/v1/analytics/eoq/?sku=<SKU>` | Wilson EOQ batch sizing and ESG carbon emissions |
| `GET` | `/api/v1/purchase-orders/` | List all purchase orders across drafts, approved, and transmitted |
| `POST` | `/api/v1/purchase-orders/<id>/transmit/` | Approve and transmit purchase order to vendor |
| `GET` | `/api/v1/purchase-orders/<id>/export-edi/` | View and export raw ANSI X12 EDI 850 document |
| `GET` | `/api/v1/stock-transfers/` | View pending and dispatched inter-warehouse transfers |
| `POST` | `/api/v1/stock-transfers/<id>/execute/` | Dispatch warehouse transfer and debit donor stock |

---

## 8. Step-by-Step Operator Guide

### 8.1. Routine Morning Monitoring (30 Seconds)
1. Open the StockSense dashboard: [http://127.0.0.1:8000/](http://127.0.0.1:8000/).
2. Glance at the **Executive Summary**:
   - Check **Stockout Alerts** (Green: 0 critical; Red: items need replenishment).
   - Check **Business Protection** (Protected $\ge 80\%$).
3. If Auto-Pilot is engaged, review the **Autonomous Activity Stream** to see what purchase orders and stock transfers the AI executed overnight.

### 8.2. Running an On-Demand Sweep
- Click **"Run Auto-Pilot Cycle"** in the top navbar or **"Run Autonomous Sweep"** in the hero section.
- StockSense scans the entire catalog, recalculates daily burn rates, evaluates pending shipments, and automatically approves and transmits POs within your set budget ceiling.

### 8.3. Adjusting Auto-Pilot Guardrails
- In the **Auto-Pilot Controls** section:
  - Adjust the **Auto-Approve Under** ceiling ($5,000 to $100,000 per order).
  - Use **Pause Auto-Pilot** if you wish to temporarily hold all orders for manual review.

### 8.4. Simulating Supply Chain Shocks
- Under **"What-If" Stress Test Simulation**, click:
  - **Scenario A**: Simulates viral demand surge (+40%).
  - **Scenario B**: Simulates port clearance bottleneck (+14 days).
  - **Scenario C**: Simulates supplier halt and tests failover to domestic backup vendors.
- StockSense instantly calculates the revised stockout date and recommends optimal dynamic safety stocks.
