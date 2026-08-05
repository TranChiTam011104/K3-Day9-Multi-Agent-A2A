# Multi-Agent Architecture for E-commerce Dispute Resolution

## 1. Agent Roles

### 1.1 Coordinator Agent
- **Role**: Main orchestrator
- **Responsibilities**:
  - Receive customer cases
  - Coordinate workflow between specialized agents
  - Aggregate outputs and make final decisions
- **Access**: All data sources

### 1.2 Order & Seller Agent
- **Role**: Order data analyzer
- **Responsibilities**:
  - Retrieve order details from Olist dataset
  - Validate order status (canceled, unavailable, delivered, etc.)
  - Extract item information and seller IDs
  - Calculate financial totals (item + freight)
- **Access**: `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_sellers_dataset.csv`
- **Output**: Order status, items count, seller IDs, financials

### 1.3 Delivery Agent
- **Role**: Delivery timing analyzer
- **Responsibilities**:
  - Analyze delivery performance
  - Compare actual delivery with estimated delivery date
  - Determine seller handoff timing vs shipping limit
  - Identify responsible party (seller vs logistics)
- **Access**: Order delivery timestamps, shipping limit dates
- **Output**: is_late_delivery, late_sellers, on_time_sellers, delivery_margin_days

### 1.4 Payment Agent
- **Role**: Payment reconciliation checker
- **Responsibilities**:
  - Count payment rows
  - Calculate payment total vs item + freight
  - Check reconciliation within tolerance (0.10 BRL)
- **Access**: `olist_order_payments_dataset.csv`
- **Output**: payments_count, is_reconciled, difference_brl

### 1.5 Policy Agent
- **Role**: Business rule engine
- **Responsibilities**:
  - Apply EC_POLICY_V1 rules in priority order
  - Determine primary issue
  - Calculate refund amount
  - Assign responsible party
- **Access**: All agent outputs
- **Output**: PolicyResult with primary_issue, confidence, refund, responsible_party

### 1.6 Verifier Agent
- **Role**: Output validator
- **Responsibilities**:
  - Validate evidence IDs format
  - Verify evidence exists in CSV files
  - Check schema compliance
  - Validate financial totals
- **Access**: Generated outputs, CSV data

---

## 2. Agent Handoff Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           COORDINATOR AGENT                              │
│                    (Receives case, orchestrates workflow)                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ORDER & SELLER AGENT                             │
│         (get_order_with_details → order data, financials)                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────────┐
│       DELIVERY AGENT             │  │         PAYMENT AGENT               │
│ (analyze_delivery_timing)        │  │ (check_payment_reconciliation)      │
│                                 │  │                                     │
│ - is_late_delivery              │  │ - payments_count                    │
│ - late_sellers                  │  │ - is_reconciled                     │
│ - on_time_sellers               │  │ - difference_brl                    │
└─────────────────────────────────┘  └─────────────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          POLICY AGENT                                    │
│            (apply_policy → primary_issue, confidence, refund)             │
│                                                                          │
│  Priority Rules (EC_POLICY_V1):                                         │
│  1. canceled_order_paid    → platform, full refund                      │
│  2. unavailable_order_paid → platform, full refund                      │
│  3. late_delivery_seller   → seller, freight refund                     │
│  4. late_delivery_logistics → logistics, freight refund                  │
│  5. valid_split_payment    → no action, explain                         │
│  6. unsupported_late_claim → no action, reject                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       VERIFIER AGENT                                     │
│         (validate_output_schema → build_output → write_output)            │
│                                                                          │
│  - Evidence ID validation                                                │
│  - Schema compliance check                                              │
│  - Financial totals verification                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          OUTPUT                                          │
│              (output/EC_XXX.json with all required fields)              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Confidence Calculation (Multi-Agent Evidence)

Confidence is calculated based on evidence quality from all agents:

### 3.1 Order Agent Confidence
- Base: 0.80
- +0.10 if has items
- +0.10 if has seller info

### 3.2 Payment Agent Confidence
- Base: 0.85
- +0.13 for perfect reconciliation (diff = 0)
- +0.10 for near-perfect (diff <= 0.01)
- +0.05 for good reconciliation (diff <= 0.05)
- +0.02 for split payment with reconciliation

### 3.3 Delivery Agent Confidence
- Base: 0.85
- +0.05 if has estimated and delivered dates
- +0.05 if has carrier date
- +0.05 if has shipping limits

### 3.4 Cross-Agent Confidence
- Weighted average: order(0.25) + payment(0.25) + delivery(0.30) + policy(0.20)
- Boost: +5% if all agents have ≥0.9 confidence

### 3.5 Policy Match Quality
- Deterministic cases (canceled/unavailable): 1.0
- Late delivery with evidence: 0.95
- Late delivery contradicting: 0.3
- Payment reconciled: 0.95
- Payment not reconciled: 0.5

---

## 4. Decision Flow

### 4.1 Case EC_XXX Processing

```
START: case_id = "EC_XXX"
       claimed_order_id from input

→ Fetch order data
  ├─ Order exists? NO → ERROR
  └─ Order exists? YES → Continue

→ Check order_status
  ├─ status = "canceled" AND payment > 0 → ISSUE: canceled_order_paid
  ├─ status = "unavailable" AND payment > 0 → ISSUE: unavailable_order_paid
  └─ status = "delivered" → Continue to delivery check

→ Check delivery timing
  ├─ is_late = TRUE AND late_sellers exist → ISSUE: late_delivery_seller
  ├─ is_late = TRUE AND no late_sellers → ISSUE: late_delivery_logistics
  └─ is_late = FALSE → Continue to payment check

→ Check payment reconciliation
  ├─ payments >= 2 AND reconciled → ISSUE: valid_split_payment
  └─ Otherwise → ISSUE: unsupported_late_claim

→ Calculate confidence from multi-agent evidence
→ Build output with evidence IDs
→ Validate schema
→ Write to output/EC_XXX.json

END
```

---

## 5. Policy Version

**EC_POLICY_V1**

| Priority | Issue | Condition | Responsible | Refund | Action |
|----------|-------|-----------|-------------|--------|--------|
| 1 | canceled_order_paid | status=canceled, payment>0 | platform | payment_total | issue_full_refund |
| 2 | unavailable_order_paid | status=unavailable, payment>0 | platform | payment_total | issue_full_refund |
| 3 | late_delivery_seller | late AND seller handover late | seller | freight_total | refund_freight |
| 4 | late_delivery_logistics | late AND seller on time | logistics | freight_total | refund_freight |
| 5 | valid_split_payment | ≥2 payments, reconciled | none | 0 | explain_valid_split_payment |
| 6 | unsupported_late_claim | not late, reconciled | none | 0 | reject_late_refund |
