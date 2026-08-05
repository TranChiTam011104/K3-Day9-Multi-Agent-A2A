# Architecture: Multi-Agent E-commerce Dispute Resolution

## Model

**`gpt-4o-mini`** — OpenAI Small class model (< 8B parameter equivalent), provided via OpenAI API.
Declared in source code (`src/llm_client.py`) as required by lab rules. Uses JSON mode (`response_format: json_object`) for structured output.

## Sơ đồ Agent và Luồng Handoff

```
┌─────────────────────────────────────────────────────┐
│              COORDINATOR AGENT                      │
│  - Đọc input/EC_XXX.json                            │
│  - Load dữ liệu CSV qua data_loader                 │
│  - Điều phối luồng agent                            │
│  - Ghi output/EC_XXX.json                           │
└───┬──────────────────────────────────────────────────┘
    │ context = {case_id, order_id, order_data (from CSV)}
    ▼
┌─────────────────────────────────────────────────────┐
│         ORDER & SELLER AGENT (LLM Call #1)          │
│  Input:  order_status, items, shipping_limit_date,  │
│          order_delivered_carrier_date               │
│  LLM Task: Phân loại từng seller: "late"/"on_time" │
│            dựa trên carrier_date vs limit_date      │
│  Output: order_status, late_sellers[], on_time_sellers[] │
└───┬─────────────────────────────────────────────────┘
    │ handoff: + order_seller_analysis
    ▼
┌─────────────────────────────────────────────────────┐
│           PAYMENT AGENT (LLM Call #2)               │
│  Input:  payment rows, item_total, freight_total    │
│  LLM Task: Tính tổng payment, kiểm tra reconcile   │
│            |payment - (item+freight)| <= 0.10 BRL  │
│            Xác định split payment (>= 2 rows)      │
│  Output: payments_count, total_payment_brl,         │
│          is_reconciled, is_split_payment            │
└───┬─────────────────────────────────────────────────┘
    │ handoff: + payment_analysis
    ▼
┌─────────────────────────────────────────────────────┐
│           DELIVERY AGENT (LLM Call #3)              │
│  Input:  delivered_customer_date, estimated_date    │
│  LLM Task: So sánh 2 timestamps, xác định          │
│            delivered_customer > estimated?          │
│  Output: is_late_delivery, days_late                │
└───┬─────────────────────────────────────────────────┘
    │ handoff: + delivery_analysis
    ▼
┌─────────────────────────────────────────────────────┐
│           POLICY AGENT (LLM Call #4)                │
│  Input:  Tất cả evidence từ 3 agents trên           │
│  LLM Task: Áp dụng EC_POLICY_V1 theo thứ tự        │
│            ưu tiên (6 rules):                       │
│            1. canceled_order_paid                   │
│            2. unavailable_order_paid                │
│            3. late_delivery_seller                  │
│            4. late_delivery_logistics               │
│            5. valid_split_payment                   │
│            6. unsupported_late_claim                │
│  Output: primary_issue, responsible_party,          │
│          recommended_refund_brl, resolution_action  │
└───┬─────────────────────────────────────────────────┘
    │ handoff: + policy_result
    ▼
┌─────────────────────────────────────────────────────┐
│           VERIFIER AGENT (LLM Call #5)              │
│  Input:  Draft output JSON                          │
│  LLM Task: Validate schema, evidence ID formats,   │
│            limits (max 10 evidence, 5 per entity), │
│            financial consistency                    │
│  + Deterministic safety checks (post-LLM)          │
│  Output: final validated JSON                       │
└───┬─────────────────────────────────────────────────┘
    │
    ▼
 output/EC_XXX.json
```

## Vai trò mỗi Agent

| Agent | File | Quyền truy cập dữ liệu | Đầu ra |
|-------|------|------------------------|--------|
| Coordinator | `src/agents/coordinator.py` | Toàn bộ CSV (qua data_loader) | Điều phối, ghi output file |
| OrderSellerAgent | `src/agents/order_seller_agent.py` | order_status, items, shipping_limit_date, carrier_date | late_sellers, on_time_sellers |
| PaymentAgent | `src/agents/payment_agent.py` | payment rows, item prices, freight values | payments_count, is_reconciled, totals |
| DeliveryAgent | `src/agents/delivery_agent.py` | delivered_customer_date, estimated_delivery_date | is_late_delivery |
| PolicyAgent | `src/agents/policy_agent.py` | Output từ 3 agents trên | primary_issue, refund, action |
| VerifierAgent | `src/agents/verifier_agent.py` | Draft output JSON | Validated final JSON |

## Handoff Protocol

Mỗi agent nhận một **context dict** từ agent trước (pass-by-reference), bổ sung kết quả phân tích vào key riêng, và trả về context cho agent tiếp theo:

```python
context = {
    "case_id": "EC_001",
    "order_id": "<uuid>",
    "order_data": {...},           # Loaded by Coordinator
    "order_seller_analysis": {...}, # Added by OrderSellerAgent
    "payment_analysis": {...},      # Added by PaymentAgent
    "delivery_analysis": {...},     # Added by DeliveryAgent
    "policy_result": {...},         # Added by PolicyAgent
    "final_output": {...},          # Added by VerifierAgent
}
```

## LLM Client

**File:** `src/llm_client.py`

- SDK: `google-genai` (mới nhất, không deprecated)
- JSON mode (`response_mime_type="application/json"`)
- Temperature 0.0 để đảm bảo tính nhất quán
- Retry logic với exponential backoff khi gặp rate limit

## Cấu trúc thư mục

```
K3-Day9-Multi-Agent-A2A/
├── run.py                    # Entry point
├── metadata.json             # Model info
├── architecture.md           # File này
├── trace.jsonl               # Execution log (overwrite mỗi lần chạy)
├── requirements.txt
├── src/
│   ├── llm_client.py         # Gemini API wrapper
│   ├── data_loader.py        # CSV loader + cache
│   ├── trace_logger.py       # JSONL trace writer
│   ├── validators.py         # Schema validators
│   ├── output_writer.py      # Output file writer
│   ├── policy.py             # Policy enums/dataclasses
│   └── agents/
│       ├── coordinator.py    # Pipeline orchestrator
│       ├── order_seller_agent.py
│       ├── payment_agent.py
│       ├── delivery_agent.py
│       ├── policy_agent.py
│       └── verifier_agent.py
├── input/                    # EC_001.json ... EC_050.json
├── output/                   # EC_001.json ... EC_050.json (generated)
└── data/                     # 9 Olist CSV files
```
