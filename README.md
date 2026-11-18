# StockSense — Autonomous Inventory Intelligence & Supply Chain Platform

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Django 5.1](https://img.shields.io/badge/Django-5.1-092E20.svg?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Tests Passing](https://img.shields.io/badge/Tests-31%20Passed-30d158.svg)](#test-suite--quality-assurance)
[![Design](https://img.shields.io/badge/Design-Apple%20Pro%20Dark-000000.svg?logo=apple&logoColor=white)](https://apple.com)

**Autonomous inventory optimization that eliminates static reorder points through collaborative Multi-Agent AI, dynamic Days of Cover (DoC), autonomous ANSI X12 EDI 850 execution, and real-time revenue protection.**

[Quick Start](#-quick-start-one-command-launch) • [Architecture](#-system-architecture) • [Unique AI Features](#-competitive-superpowers-why-stocksense-defeats-legacy-tools) • [The 9 Analytical Engines](#-the-9-deep-dive-analytical-engines) • [API Reference](#-complete-23-endpoint-rest-api-reference)

</div>

---

## 📖 Table of Contents
1. [The Problem with Traditional Inventory Software](#-the-problem-with-traditional-inventory-software)
2. [Competitive Superpowers: Why StockSense Defeats Legacy Tools](#-competitive-superpowers-why-stocksense-defeats-legacy-tools)
3. [Quick Start (One-Command Launch)](#-quick-start-one-command-launch)
4. [System Architecture & End-to-End Flow](#-system-architecture)
5. [The Multi-Agent Cognitive Replenishment Engine](#-the-multi-agent-cognitive-replenishment-engine)
6. [Unique AI Capabilities](#-unique-ai-capabilities)
   - [Natural Language StockSense Copilot](#1-natural-language-stocksense-copilot)
   - [Volume Discount Arbitrage & Autonomous Supplier Negotiation](#2-volume-discount-arbitrage--autonomous-supplier-negotiation)
   - [Revenue at Risk & Wasted Paid Ad Spend Shield](#3-revenue-at-risk--wasted-paid-ad-spend-shield)
7. [Autonomous Auto-Pilot Subsystem & ANSI X12 EDI 850](#-autonomous-auto-pilot-subsystem)
8. [The 9 Deep Dive Analytical Engines](#-the-9-deep-dive-analytical-engines)
9. [Apple Pro Design System & UI Architecture](#-apple-pro-design-system--ui-architecture)
10. [Complete 23-Endpoint REST API Reference](#-complete-23-endpoint-rest-api-reference)
11. [Test Suite & Quality Assurance](#-test-suite--quality-assurance)

---

## 🛑 The Problem with Traditional Inventory Software

Traditional inventory systems (Netstock, Slimstock, SAP, Blue Yonder, and ERP spreadsheet exports) rely on **static Min/Max thresholds** or fixed **Reorder Points (ROP)** configured once a year.

In reality:
- **Customer demand fluctuates violently**: Viral spikes, seasonal shifts, and promotions burn through inventory before static rules flag a warning.
- **Supplier lead times are volatile**: Port congestion, customs holds, and factory backlogs create supply deficits that static formulas ignore.
- **Legacy tools express problems in units, not dollars**: Telling an executive "SKU-101 is short 120 units" fails to communicate that **\$18,450 in gross margin is about to be lost** and **\$2,200 in active Google/Meta ad spend is pointing to out-of-stock pages**.
- **No execution automation**: Legacy tools only output dense recommendation lists requiring hours of manual clicks to approve, write emails, and file purchase orders.

**StockSense solves this by creating a closed-loop autonomous system** that continuously evaluates burn rates, protects revenue, drafts supplier negotiations, and transmits EDI transactions without manual friction.

---

## ⚡ Competitive Superpowers: Why StockSense Defeats Legacy Tools

| Feature / Capability | Legacy ERPs (SAP / Oracle) | Mid-Market Tools (Netstock / Slimstock) | **StockSense Autonomous Platform** |
|---|---|---|---|
| **Inventory Thresholds** | Static Min / Max thresholds | Simple moving averages | **Dynamic Days of Cover (DoC)** recalculating daily with lead-time volatility ($\sigma_L$) and empirical demand burn ($\sigma_d$) |
| **Safety Stock Model** | Fixed buffer units (e.g., 20 units) | Static standard deviation | **King's Formula Dynamic Buffer**: $Z \cdot \sqrt{L_{\text{eff}} \cdot \sigma_d^2 + \bar{d}^2 \cdot \sigma_L^2}$ factoring live disruption delays |
| **Execution** | Manual purchase order drafting & manual emails | Suggestion lists requiring human clicks | **Zero-Touch Auto-Pilot Engine**: Autonomous policy guardrails, ANSI X12 EDI 850 transmission, and intra-warehouse transfers |
| **Supplier Negotiation** | None | None | **AI Volume Discount Arbitrage**: Analyzes tier price breaks vs. holding costs and drafts executive negotiation memos |
| **Financial Translation** | Units only ("short 150 units") | Units only | **Revenue at Risk Shield**: Translates shortages into lost top-line $, lost margin $, and wasted paid ad spend $ |
| **Executive Experience** | Dense tables requiring weeks of training | Complex spreadsheet grids | **Natural Language Copilot + Apple Pro Glassmorphism**: Ask plain English questions, get answers and 1-click execution |
| **Disruption Monitoring** | Post-facto notification | None | **pgvector Semantic RAG**: Real-time vector search across geopolitical & port disruption news feeds |

---

## 🚀 Quick Start (One-Command Launch)

StockSense includes an all-in-one platform runner that validates your environment, applies database migrations, seeds synthetic inventory data, and starts the Django web server and Celery background workers:

```bash
# Clone the repository
git clone git@github.com:AarushPadhy/StockSense.git
cd StockSense

# Single command to boot everything
./start.sh
```

*Or via the custom Django management command:*
```bash
python manage.py run_platform
```

Once started, open your browser to:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph DataIngestion ["1. High-Speed Data Ingestion"]
        CSV[CSV / ERP Feeds] --> Polars[Polars Multi-Threaded Engine]
        Polars --> DB[(TimescaleDB / PostgreSQL)]
        News[Global Disruption Feeds] --> PgVector[(pgvector 1536d Cosine Embeddings)]
    end

    subgraph MultiAgentEngine ["2. Multi-Agent Replenishment Pipeline"]
        DB --> DA[Demand Forecasting Agent]
        DB --> IA[Inventory Health & Resilience Agent]
        PgVector --> IA
        DA --> PA[Planning & Sourcing Agent]
        IA --> PA
        PA --> Decision[Procurement Plan & CoT Explanation]
    end

    subgraph UniqueAIEngines ["3. Unique AI Superpowers"]
        Decision --> Arbitrage[AI Volume Discount Arbitrageur]
        Decision --> RevShield[Revenue at Risk & Ad Spend Shield]
        Decision --> Copilot[StockSense Natural Language Copilot]
    end

    subgraph AutoPilotExecution ["4. Autonomous Auto-Pilot Subsystem"]
        Decision --> PolicyCheck{AutoPilotPolicy Guardrails}
        PolicyCheck -- Under Budget Ceiling -- --> AutoApprove[Autonomous Execution Engine]
        PolicyCheck -- Over Ceiling -- --> ManualQueue[Pending Executive Review]
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

## 🧠 The Multi-Agent Cognitive Replenishment Engine

StockSense runs three collaborative agents for every catalog SKU:

### 1. Demand Forecasting Agent (`DemandForecaster`)
- Analyzes 90-day daily sales history using Polars SIMD acceleration.
- Computes empirical daily sales average ($\bar{d}$), demand variance ($\sigma_d$), and linear velocity trend factor ($\beta$).
- Detects demand acceleration to avoid under-forecasting during viral sales periods.

### 2. Inventory Health & Resilience Agent (`King's Dynamic Safety Stock`)
- Computes **Effective Lead Time** factoring in active global disruption flags ($\Delta L$):
  $$L_{\text{effective}} = L + \Delta L$$
- Calculates real-time **Dynamic Days of Cover (DoC)**:
  $$\text{DoC} = \frac{\text{Current Stock} - \text{Allocated Stock}}{\text{Forecasted Daily Demand}}$$
- Evaluates **King's Formula Dynamic Safety Stock ($SS$)**:
  $$SS = Z \cdot \sqrt{L_{\text{effective}} \cdot \sigma_d^2 + \bar{d}^2 \cdot \sigma_L^2}$$
  *(where $Z = 1.645$ for 95% cycle service level, or $2.054$ for 98%)*
- Sets **Dynamic Reorder Point ($ROP$)**:
  $$ROP = (\bar{d} \cdot L_{\text{effective}}) + SS$$

### 3. Planning & Procurement Agent (`MultiAgentSupplyChainOrchestrator`)
- Evaluates supplier contracts, Minimum Order Quantities (MOQ), volume tier pricing breaks, and corridor risk indices.
- Computes replenishment quantity:
  $$Q = \max(\text{MOQ}, \lceil ROP - \text{Current Stock} + (\bar{d} \cdot \text{Target Cover Days}) \rceil)$$
- Generates a plain-English **Chain-of-Thought (CoT)** reasoning narrative explaining the full decision trail.

---

## 🌟 Unique AI Capabilities

### 1. Natural Language StockSense Copilot
Executives and non-technical business owners can query their live supply chain in plain English directly from the top of the dashboard:
- *"Which products will run out of stock first?"* $\to$ Ranks vulnerable catalog items with exact runway countdowns and 1-click restock buttons.
- *"How much money and capital is needed for purchase orders?"* $\to$ Aggregates pending PO capital, historical auto-pilot spend, and top-line exposure.
- *"Which supplier is the slowest or most risky?"* $\to$ Ranks vendor lead times, OTIF delivery percentages, and disruption risks.
- *"What actions did Auto-Pilot execute recently?"* $\to$ Returns recent autonomous EDI 850 transmissions and warehouse transfers.

### 2. Volume Discount Arbitrage & Autonomous Supplier Negotiation
Unlike tools that reorder fixed batches, StockSense analyzes supplier quantity tiers:
- Compares Standard Batch ($Q_1$), Volume Arbitrage ($1.5 \times Q_1$), and Bulk Scale ($2.2 \times Q_1$).
- Calculates the trade-off between gross purchasing savings and incremental working capital holding costs:
  $$\text{Net Arbitrage Gain} = \Delta \text{Price} \cdot Q_{\text{tier}} - (\Delta \text{Capital} \cdot h_{\text{holding}})$$
- **Autonomous Supplier Negotiation Memo**: Automatically drafts an executive correspondence with committed PO volumes, freight dock consolidation benefits, and EDI confirmation ready for transmission.

### 3. Revenue at Risk & Wasted Paid Ad Spend Shield
Translates unit stockouts into executive financial exposure:
1. **Top-Line at Risk**: $\text{Units Short} \times \text{Unit Retail Price}$
2. **Gross Margin at Risk**: $\text{Units Short} \times (\text{Retail Price} - \text{Unit Cost})$
3. **Wasted Paid Ad Spend**: Estimates marketing dollars burning on Google/Meta ads pointing customers to depleted landing pages ($\sim 12\%$ of lost revenue).
4. **Customer LTV Churn**: Quantifies customer defect hazard when unfulfilled buyers purchase from competitors.
5. **1-Click Shield Execution**: Dispatches priority inter-hub transfers or emergency expedited supplier orders to prevent the stockout before it happens.

---

## 🤖 Autonomous Auto-Pilot Subsystem

The Auto-Pilot engine enables hands-free supply chain operations within safe business guardrails:

### Guardrails & Policy Configuration (`AutoPilotPolicy`)
- `is_enabled`: Master power switch (Active vs. Paused).
- `max_auto_po_value_usd`: Financial ceiling per single purchase order (e.g., $15,000). Any order exceeding this limit is held in `PENDING_APPROVAL` for manual executive sign-off.
- `auto_approve_po`: Permission flag to approve qualified purchase orders autonomously.
- `auto_dispatch_transfers`: Permission flag to balance inter-warehouse stock across regional hubs.
- `require_trusted_supplier_only`: Restricts automatic PO transmission to Tier-1 vendors with OTIF delivery records $>90\%$.

### ANSI X12 EDI 850 Transaction Generation
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

### Multi-Hub Intra-Network Stock Transfers
Rather than paying rush air-freight fees to overseas suppliers when a regional hub runs low, StockSense evaluates surplus stock at nearby company warehouses and dispatches low-cost ground freight transfers, saving up to 85% in logistics expenses.

---

## 📊 The 9 Deep Dive Analytical Engines

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

## 🎨 Apple Pro Design System & UI Architecture

The user interface of StockSense is built using Apple's "Pro" dark-mode aesthetics:
- **Canvas**: True pitch-black `#000000` with high-contrast optical hierarchy.
- **Materials**: Multi-layered frosted glass (`backdrop-filter: blur(28px)`) with hairline specular highlights (`rgba(255, 255, 255, 0.08)`).
- **Typography**: San Francisco (`-apple-system`, `SF Pro Display`, `SF Pro Text`, `SF Mono`).
- **Interactive Physics**: Cubic-bezier fluid transitions (`cubic-bezier(0.16, 1, 0.3, 1)`) with `active:scale-[0.97]` tactile click feedback.
- **Dual Perspective Modes**:
  - **Executive (Simple)**: Plain-English summaries, runway countdowns, live health indices, and 1-click replenishment.
  - **Deep Dive (Analyst)**: Detailed data matrices, Wilson EOQ batches, EDI transaction inspectors, and OTIF compliance.

---

## 🔌 Complete 23-Endpoint REST API Reference

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

## 🧪 Test Suite & Quality Assurance

StockSense includes an automated test suite verifying models, multi-agent services, autonomous execution, and all 23 API endpoints:

```bash
# Run all 31 unit and integration tests
./venv/bin/python manage.py test tests

# Output:
# Found 31 test(s).
# ...............................
# Ran 31 tests in 0.906s
# OK

# Run the live endpoint verification script
./venv/bin/python verify_endpoints.py

# Output:
# ==========================================
# VERIFICATION SUMMARY: 23 PASSED, 0 FAILED
# ==========================================
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

<div align="center">

**StockSense** • Autonomous Inventory Intelligence • Built for Modern Commerce

</div>
