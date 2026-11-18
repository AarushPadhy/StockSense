# StockSense — Application Architecture & In-Depth Operation Manual

---

## 1. Executive Summary & Philosophy

**StockSense** is an autonomous inventory intelligence and supply chain optimization platform. Traditional inventory management systems (Netstock, Slimstock, SAP, Blue Yonder) rely on rigid, static Reorder Points (ROP) that inevitably fail during sudden demand spikes, shipping congestion, or geopolitical disruptions. 

StockSense replaces manual spreadsheets and static rules with a continuous, closed-loop multi-agent cognitive architecture:
1. **Dynamic Days of Cover (DoC)** replaces static min/max thresholds.
2. **Multi-Agent Collaborative Intelligence** (Demand Agent, Inventory Health Agent, Planning Agent) reasons through replenishment decisions in plain English.
3. **Autonomous Auto-Pilot Execution** transmits approved Purchase Orders via enterprise ANSI X12 EDI 850 protocols and balances regional warehouse inventory via inter-hub transfers.
4. **Unique AI Superpowers**: Built-in Natural Language Copilot, Volume Discount Arbitrage with automated supplier negotiation letters, and real-time Lost Revenue & Ad Spend Waste shields.
5. **Apple-Grade Executive Interface** gives business owners immediate clarity without cognitive clutter, while preserving deep technical telemetry for analysts.

---

## 2. Competitive Superpowers: StockSense vs. Legacy Tools

| Capability | Legacy ERPs (SAP / Oracle) | Mid-Market Tools (Netstock / Slimstock) | **StockSense Autonomous Platform** |
|---|---|---|---|
| **Inventory Thresholds** | Static Min / Max limits configured once a year | Static formulas with historical averages | **Dynamic Days of Cover (DoC)** continuously adjusted for lead-time variance & burn rate |
| **Execution** | Manual purchase order drafting & manual emails | Suggestion lists requiring human clicks | **Zero-Touch Auto-Pilot**: Autonomous approval, ANSI X12 EDI 850 transmission, and stock transfers |
| **Supplier Negotiation** | None | None | **AI Volume Discount Arbitrage**: Evaluates tier price breaks vs. holding costs and drafts negotiation letters |
| **Financial Impact** | Unit quantities only (e.g. "short 120 units") | Unit quantities only | **Revenue at Risk Shield**: Translates stockouts into lost top-line $, lost margin $, and wasted paid ad spend $ |
| **Executive Interface** | Complex tables requiring technical training | Dense multi-column grids | **Natural Language Copilot + Apple Pro Glassmorphism**: Ask plain English questions, get answers and 1-click actions |
| **Disruption Monitoring** | Post-facto notification | None | **pgvector RAG + King's formula**: Semantic news search and automated supplier corridor rerouting |

---

## 3. End-to-End System Architecture

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

    subgraph UniqueAIEngines ["3. Unique AI Intelligence Layer"]
        Decision --> Arbitrage[AI Volume Discount Arbitrageur]
        Decision --> RevShield[Revenue at Risk & Ad Spend Shield]
        Decision --> Copilot[StockSense Natural Language Copilot]
    end

    subgraph AutoPilotExecution ["4. Autonomous Auto-Pilot Subsystem"]
        Decision --> PolicyCheck{AutoPilotPolicy Guardrails}
        PolicyCheck -- Within Ceiling -- --> AutoApprove[Autonomous Execution Engine]
        PolicyCheck -- Above Ceiling -- --> ManualQueue[Pending Executive Review]
        AutoApprove --> EDI[ANSI X12 EDI 850 Generator]
        AutoApprove --> Transfers[Multi-Hub Stock Transfers]
        AutoApprove --> AuditLog[AutonomousActionLog Immutable Audit]
    end

    subgraph PresentationLayer ["5. Apple-Grade Executive Interface"]
        AuditLog --> UI[StockSense Command Center]
        EDI --> UI
        Arbitrage --> UI
        RevShield --> UI
        Copilot --> UI
        UI --> ExecMode[Executive Simple Overview]
        UI --> DeepDive[9 Technical Analyst Modules]
    end
```

---

## 4. The Multi-Agent Cognitive Architecture

The replenishment pipeline executes three collaborative agents for every tracked SKU:

### 4.1. Demand Forecasting Agent (`DemandForecaster`)
- **Input**: 90-day historical sales transaction stream.
- **Computation**:
  - Daily sales average: $\bar{d} = \frac{1}{N}\sum_{i=1}^N d_i$
  - Demand variance ($\sigma_d$) and standard deviation.
  - Linear velocity trend factor ($\beta$) via empirical regression.
- **Output**: Forecasted daily burn rate and forecast volatility index.

### 4.2. Inventory Health & Resilience Agent (`King's Dynamic Safety Stock`)
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

### 4.3. Planning & Procurement Agent (`MultiAgentSupplyChainOrchestrator`)
- Evaluates primary and secondary vendor contracts, Minimum Order Quantities (MOQ), volume tier pricing breaks, and corridor risk indices.
- If current stock $\le ROP$, generates a precise replenishment quantity:
  $$Q = \max(\text{MOQ}, \lceil ROP - \text{Current Stock} + (\bar{d} \cdot \text{Target Cover Days}) \rceil)$$
- Synthesizes a human-readable **Chain-of-Thought (CoT)** reasoning narrative explaining *why* the order is needed and *which* supplier was selected.

---

## 5. Unique AI Capabilities (Detailed Engines)

### 5.1. Autonomous AI Volume Discount Arbitrageur (`AIVolumeDiscountArbitrageur`)
Unlike traditional tools that blindly reorder small batches, StockSense analyzes supplier quantity tiers:
- Compares Standard Batch ($Q_1$), Volume Arbitrage ($1.5 \times Q_1$), and Bulk Scale ($2.2 \times Q_1$).
- Calculates the trade-off between gross purchasing savings and incremental working capital holding costs:
  $$\text{Net Arbitrage Gain} = \Delta \text{Price} \cdot Q_{\text{tier}} - (\Delta \text{Capital} \cdot h_{\text{holding}})$$
- **Autonomous Supplier Negotiation Memo**: Automatically drafts an executive correspondence with committed PO volumes, logistics consolidation benefits, and EDI confirmation ready for transmission.

### 5.2. Lost Revenue & Wasted Ad Spend Shield (`RevenueRiskEngine`)
Translates unit stockouts into executive financial exposure:
1. **Top-Line at Risk**:
   $$\text{Revenue at Risk} = \text{Units Short} \times \text{Unit Retail Price}$$
2. **Gross Margin at Risk**:
   $$\text{Margin at Risk} = \text{Units Short} \times (\text{Retail Price} - \text{Unit Cost})$$
3. **Wasted Paid Ad Spend**: Estimates marketing dollars burning on Google/Meta ads pointing customers to depleted landing pages ($\sim 12\%$ of lost revenue).
4. **Customer LTV Churn**: Quantifies customer defect hazard when unfulfilled buyers purchase from competitors.
5. **1-Click Shield Execution**: Dispatches priority inter-hub transfers or emergency expedited supplier orders to prevent the stockout before it happens.

### 5.3. Natural Language StockSense Copilot (`StockSenseCopilot`)
An embedded conversational copilot that understands natural language questions and returns real-time computed data:
- *"Which products will run out first?"* $\to$ Ranks vulnerable catalog items with exact runway countdowns and 1-click restock buttons.
- *"How much money is needed for purchase orders?"* $\to$ Aggregates pending PO capital, historical auto-pilot spend, and top-line exposure.
- *"Which supplier is the slowest or most risky?"* $\to$ Ranks vendor lead times, OTIF delivery percentages, and disruption risks.
- *"What did Auto-Pilot execute today?"* $\to$ Returns recent autonomous EDI 850 transmissions and warehouse transfers.

---

## 6. Autonomous Auto-Pilot Subsystem

The Auto-Pilot engine enables hands-free supply chain operations within safe business guardrails:

### 6.1. Guardrails & Configuration (`AutoPilotPolicy`)
- `is_enabled`: Master power switch (Active vs. Paused).
- `max_auto_po_value_usd`: Financial ceiling per single purchase order (e.g., $15,000). Any order exceeding this limit is held in `PENDING_APPROVAL` for manual executive sign-off.
- `auto_approve_po`: Permission flag to approve qualified purchase orders autonomously.
- `auto_dispatch_transfers`: Permission flag to balance inter-warehouse stock across regional hubs.
- `require_trusted_supplier_only`: Restricts automatic PO transmission to Tier-1 vendors with OTIF delivery records $>90\%$.

### 6.2. ANSI X12 EDI 850 Transaction Generation
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

### 6.3. Multi-Hub Intra-Network Stock Transfers
Rather than paying rush air-freight fees to overseas suppliers when a regional hub runs low, StockSense evaluates surplus stock at nearby company warehouses and dispatches low-cost ground freight transfers, saving up to 85% in logistics expenses.

---

## 7. Technical Deep Dive Analytical Engines

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

## 8. Complete 23-Endpoint Verified REST API Reference

All 23 endpoints are verified with 100% test success:

| Method | Endpoint | Request Body / Query Params | Description |
|---|---|---|---|
| `GET` | `/api/v1/dashboard/replenishment/` | — | Executive telemetry KPIs & digital twin resilience score |
| `GET` | `/api/v1/inventory/` | — | Product catalog with stock levels, DoC, and vendor lead times |
| `GET` | `/api/v1/automation/status/` | — | Auto-Pilot status, policy ceilings, and spend telemetry |
| `POST` | `/api/v1/automation/toggle/` | `{"is_enabled": bool, "max_auto_po_value": float}` | Enable/pause Auto-Pilot and update PO value limits |
| `POST` | `/api/v1/automation/run-cycle/` | `{"force": true}` | Manually trigger a full autonomous scanning & execution cycle |
| `GET` | `/api/v1/automation/audit-logs/` | `?limit=8&action_type=...` | Immutable audit trail of autonomous actions |
| `POST` | `/api/v1/replenishment/draft-po/` | `{"product_sku": str, "auto_draft_po": bool}` | Multi-agent replenishment calculation and PO draft |
| `POST` | `/api/v1/simulation/what-if/` | `{"product_sku": str, "demand_surge_percent": float, "lead_time_delay_days": int}` | Parametric stress testing (demand spikes, port delays) |
| `POST` | `/api/v1/ai/copilot/` | `{"query": str}` | Natural language executive copilot with real-time answers |
| `GET` | `/api/v1/ai/revenue-at-risk/` | — | Lost revenue, lost gross margin, and wasted ad spend shield |
| `POST` | `/api/v1/ai/negotiate/` | `{"product_sku": str, "planned_order_qty": int}` | Volume discount arbitrage analysis & negotiation email memo |
| `GET` | `/api/v1/analytics/abc-xyz/` | — | 9-box catalog classification matrix |
| `GET` | `/api/v1/analytics/resilience-tts/` | — | Time-to-Survive vs. Time-to-Recover resilience index |
| `GET` | `/api/v1/analytics/landed-cost/` | `?sku=<SKU>` | Global corridor delivered landed cost & tariffs |
| `GET` | `/api/v1/suppliers/scorecards/` | — | Supplier OTIF delivery rates and defect PPM |
| `GET` | `/api/v1/analytics/bullwhip/` | — | Forrester bullwhip ratios and smoothed order quantities |
| `GET` | `/api/v1/analytics/obsolescence-risk/` | — | Working capital at risk from expiry and obsolescence |
| `GET` | `/api/v1/analytics/eoq/` | `?sku=<SKU>` | Wilson EOQ batch sizing and ESG carbon emissions |
| `GET` | `/api/v1/purchase-orders/` | — | List all purchase orders across drafts, approved, and transmitted |
| `POST` | `/api/v1/purchase-orders/<id>/transmit/` | — | Approve and transmit purchase order to vendor |
| `GET` | `/api/v1/purchase-orders/<id>/export-edi/` | — | View and export raw ANSI X12 EDI 850 document |
| `GET` | `/api/v1/stock-transfers/` | — | View pending and dispatched inter-warehouse transfers |
| `POST` | `/api/v1/stock-transfers/<id>/execute/` | — | Dispatch warehouse transfer and debit donor stock |

---

## 9. Operator Guide: Using the Unique AI Features

### 9.1. Using the Copilot
1. Scroll to the **Ask StockSense Copilot** widget or click **"Ask StockSense AI"** in the top hero.
2. Click any suggested prompt chip (e.g. *🚨 Stockout Hazards* or *💰 Cash & Spend Requirements*) or type your own question in the input field.
3. The AI Copilot returns an immediate plain English answer, highlights key metrics, and displays a 1-click execution button (e.g., *Restock SKU with AI* or *Run Cycle Now*).

### 9.2. Shielding Revenue from Imminent Stockouts
1. Inspect the **Financial Exposure & Ad Spend Shield** card in the hero overview.
2. View the exact dollar figures: **Top-Line at Risk**, **Gross Margin at Risk**, and **Wasted Paid Ad Spend**.
3. Click **"Shield Revenue Now"**: StockSense executes an autonomous cycle, immediately dispatching inter-hub transfers and transmitting EDI 850 purchase orders to resolve the stockout window.

### 9.3. Negotiating Volume Discounts with AI
1. On any product card in the catalog grid, click **"Negotiate Volume Discount with AI"**.
2. An Apple Sheet will open displaying:
   - Volume tier break comparison (-8% to -15% unit cost reductions).
   - Net arbitrage gain ($) after factoring in holding costs.
   - An executive supplier negotiation email memo.
3. Click **"Copy Memo & Prepare Order"** to copy the letter to your clipboard, ready to email to your vendor account representative.
