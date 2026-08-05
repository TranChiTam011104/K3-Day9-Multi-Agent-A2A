# Architecture - Multi-Agent E-commerce Dispute Resolution

## 1. System Overview

Hệ thống multi-agent để xử lý 50 khiếu nại khách hàng Olist e-commerce. Mỗi agent phân tích một domain dữ liệu và handover bằng chứng cho agent tiếp theo.

## 2. Agent Roles

### 2.1 Coordinator Agent
- **Vai trò**: Nhận case input, giao việc, tổng hợp kết quả
- **Truy cập**: Tất cả data
- **Input**: `input/EC_XXX.json`
- **Output**: Tổng hợp từ các agent chuyên biệt

### 2.2 Order & Seller Agent
- **Vai trò**: Phân tích trạng thái đơn hàng, kiểm tra seller
- **Truy cập**: `orders.csv`, `order_items.csv`, `sellers.csv`
- **Trách nhiệm**:
  - Kiểm tra `order_status` (canceled, unavailable, delivered, ...)
  - So sánh `order_delivered_carrier_date` với `shipping_limit_date`
  - Xác định seller vi phạm
  - Trích xuất `item_ids`, `seller_ids`

### 2.3 Payment Agent
- **Vai trò**: Đối soát thanh toán
- **Truy cập**: `order_payments.csv`
- **Trách nhiệm**:
  - Tính tổng `payment_value`
  - Kiểm tra split payment (≥2 rows)
  - Verify payment = item_total + freight_total

### 2.4 Delivery Agent
- **Vai trò**: Phân tích vận chuyển
- **Truy cập**: `orders.csv`
- **Trách nhiệm**:
  - So sánh `order_delivered_customer_date` với `order_estimated_delivery_date`
  - Xác định delivery có trễ không
  - Phân biệt trách nhiệm seller vs logistics

### 2.5 Policy Agent
- **Vai trò**: Áp dụng quy tắc nghiệp vụ
- **Truy cập**: Tất cả data đã xử lý
- **Trách nhiệm**:
  - Áp dụng `EC_POLICY_V1`
  - Xác định `primary_issue`
  - Tính `recommended_refund_brl`
  - Set `case_status`, `confidence`

### 2.6 Verifier Agent
- **Vai trò**: Kiểm tra chất lượng output
- **Truy cập**: Tất cả data
- **Trách nhiệm**:
  - Validate evidence IDs (format, tồn tại)
  - Validate output schema
  - Verify financial calculations

## 3. Data Schema

### 3.1 Primary Keys & Joins

```
orders.order_id
    ├── order_items.order_id (1:N)
    │   └── products.product_id
    │   └── sellers.seller_id
    ├── order_payments.order_id (1:N)
    ├── order_reviews.order_id (1:N)
    └── customers.customer_id
        └── geolocation via zip_code_prefix
```

### 3.2 CSV Files

| File | Key Columns | Purpose |
|------|-------------|---------|
| `orders.csv` | order_id, customer_id | Trạng thái, delivery dates |
| `order_items.csv` | order_id, product_id, seller_id | Items, price, freight |
| `order_payments.csv` | order_id | Payment details |
| `order_reviews.csv` | order_id | Reviews |
| `customers.csv` | customer_id | Customer info |
| `products.csv` | product_id | Product info |
| `sellers.csv` | seller_id | Seller info |
| `geolocation.csv` | zip_code_prefix | Location data |
| `category_translation.csv` | product_category_name | Category translation |

## 4. Policy Rules (EC_POLICY_V1)

### 4.1 Priority Order

| Priority | Issue | Condition | Responsible | Refund | Action |
|----------|-------|-----------|-------------|--------|--------|
| 1 | `canceled_order_paid` | status=canceled, payment>0 | platform | payment_total | issue_full_refund |
| 2 | `unavailable_order_paid` | status=unavailable, payment>0 | platform | payment_total | issue_full_refund |
| 3 | `late_delivery_seller` | delivery_after_estimate AND carrier_date > limit | seller | freight | refund_freight |
| 4 | `late_delivery_logistics` | delivery_after_estimate AND carrier_date <= limit | logistics | freight | refund_freight |
| 5 | `valid_split_payment` | ≥2 payments, total matches | - | 0 | explain_valid_split_payment |
| 6 | `unsupported_late_claim` | delivery_on_time, payment matches | - | 0 | reject_late_refund |

### 4.2 Root Cause Codes

```
SELLER_HANDOFF_AFTER_LIMIT     → late_delivery_seller
CARRIER_DELIVERED_AFTER_ESTIMATE → late_delivery_logistics
ORDER_CANCELED_AFTER_PAYMENT    → canceled_order_paid
ORDER_UNAVAILABLE_AFTER_PAYMENT → unavailable_order_paid
MULTIPLE_PAYMENTS_RECONCILED    → valid_split_payment
DELIVERY_WITHIN_ESTIMATE        → unsupported_late_claim
```

## 5. Evidence ID Format

```
order:<order_id>
item:<order_id>:<order_item_id>
payment:<order_id>:<payment_sequential>
seller:<seller_id>
policy:<root_cause_code>
```

## 6. Handoff Flow

```
┌─────────────┐
│   INPUT     │
│ EC_XXX.json │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   COORDINATOR    │
│  (giao việc)    │
└──────┬──────────┘
       │
       ├──────────────────────┐
       │                      │
       ▼                      ▼
┌─────────────┐        ┌─────────────┐
│   ORDER &   │        │   PAYMENT   │
│   SELLER    │        │   AGENT     │
│  Agent 2-3  │        │  Agent 4-5  │
└──────┬──────┘        └──────┬──────┘
       │                      │
       └──────────┬───────────┘
                  │
                  ▼
         ┌───────────────┐
         │   DELIVERY    │
         │    AGENT      │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │    POLICY     │
         │    AGENT      │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │   VERIFIER    │
         │    AGENT      │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │    OUTPUT     │
         │ EC_XXX.json   │
         └───────────────┘
```

## 7. Agent Collaboration Matrix

| Agent | Coordinator | Order/Seller | Payment | Delivery | Policy | Verifier |
|-------|-------------|--------------|---------|----------|--------|----------|
| Coordinator | - | giao việc | giao việc | giao việc | nhận results | nhận results |
| Order/Seller | báo cáo | - | share data | share data | handover | handover |
| Payment | báo cáo | share data | - | share data | handover | handover |
| Delivery | báo cáo | share data | share data | - | handover | handover |
| Policy | kết quả | nhận data | nhận data | nhận data | - | handover |
| Verifier | kết quả | nhận data | nhận data | nhận data | nhận data | - |

## 8. File Structure

```
K3-Day9-Multi-Agent-A2A/
├── data/
│   ├── olist_orders_dataset.csv
│   ├── olist_order_items_dataset.csv
│   ├── olist_order_payments_dataset.csv
│   ├── olist_order_reviews_dataset.csv
│   ├── olist_customers_dataset.csv
│   ├── olist_products_dataset.csv
│   ├── olist_sellers_dataset.csv
│   ├── olist_geolocation_dataset.csv
│   ├── product_category_name_translation.csv
│   └── processed/              # Intermediate results
│       ├── person_2/
│       ├── person_3/
│       ├── person_4/
│       └── person_5/
├── input/
│   ├── EC_001.json ... EC_050.json
├── output/
│   ├── EC_001.json ... EC_050.json
├── src/
│   ├── __init__.py
│   ├── data_loader.py          # Load & cache CSVs
│   ├── validators.py           # Schema & evidence validation
│   ├── policy.py               # EC_POLICY_V1 rules
│   ├── output_writer.py       # Write JSON output
│   └── trace_logger.py         # Trace execution
├── architecture.md             # This file
├── metadata.json               # Model info
├── requirements.txt
├── .env.example
└── README.md
```

## 9. Output Schema

```json
{
  "case_id": "EC_XXX",
  "assessment": {
    "primary_issue": "late_delivery_seller",
    "case_status": "action_required",
    "confidence": 0.92
  },
  "affected_entities": {
    "order_ids": ["<order_id>"],
    "item_ids": ["<order_id>:1"],
    "seller_ids": ["<seller_id>"],
    "payment_ids": ["<order_id>:1"]
  },
  "root_cause_analysis": {
    "ranked_causes": [
      { "cause_code": "SELLER_HANDOFF_AFTER_LIMIT", "rank": 1 }
    ],
    "responsible_parties": [
      { "party_type": "seller", "party_id": "<seller_id>" }
    ]
  },
  "evidence_ids": [
    "order:<order_id>",
    "item:<order_id>:1",
    "payment:<order_id>:1",
    "seller:<seller_id>",
    "policy:SELLER_HANDOFF_AFTER_LIMIT"
  ],
  "financial_resolution": {
    "currency": "BRL",
    "item_total_brl": 100.0,
    "freight_total_brl": 15.0,
    "payment_total_brl": 115.0,
    "recommended_refund_brl": 15.0
  },
  "resolution_actions": ["refund_freight"]
}
```

## 10. Constraints

1. **Model size**: ≤10B parameters
2. **Evidence**: Chỉ dùng IDs có thể verify từ CSV
3. **Money rounding**: 2 decimal places
4. **Max limits**:
   - 5 IDs per entity set
   - 10 evidence IDs
   - 3 root causes
   - 3 responsible parties
   - 5 resolution actions
5. **Confidence**: [0, 1]
