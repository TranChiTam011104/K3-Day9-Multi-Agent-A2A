"""
Payment Agent
LLM phân tích payment reconciliation.
Nhiệm vụ:
- Đếm số payment rows
- Tính tổng payment_value
- So sánh với item_total + freight_total (sai số <= 0.10 BRL)
- Xác định có split payment (>= 2 rows) hay không
"""

import logging
from typing import Dict, Any

from src.llm_client import call_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Payment Reconciliation Agent for an e-commerce dispute resolution system.

You receive payment and item data from the Olist database.
Your job is to:
1. Count the number of payment rows
2. Calculate the total payment_value (sum of all payment rows)
3. Calculate expected_total = item_total_brl + freight_total_brl
4. Check if |payment_total - expected_total| <= 0.10 BRL (within tolerance)
5. Determine if this is a split payment (>= 2 payment rows)

You must respond with a valid JSON object only, no extra text.
"""

def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chạy Payment Agent.

    Args:
        context: Dict chứa order_data và các kết quả từ agent trước

    Returns:
        Context được bổ sung kết quả phân tích payment
    """
    order_data = context["order_data"]
    case_id = context["case_id"]

    payments = order_data.get("payments", [])
    financials = order_data.get("financials", {})

    payment_rows = []
    for p in payments:
        payment_rows.append({
            "payment_sequential": p.get("payment_sequential"),
            "payment_type": p.get("payment_type"),
            "payment_installments": p.get("payment_installments"),
            "payment_value": p.get("payment_value"),
        })

    user_prompt = f"""Analyze payment data for this order:

Number of payment rows: {len(payments)}
Payment rows:
{payment_rows}

Pre-calculated financials from items:
- item_total_brl: {financials.get('item_total_brl', 0.0)}
- freight_total_brl: {financials.get('freight_total_brl', 0.0)}

Calculate:
1. total_payment_brl = sum of all payment_value fields
2. expected_total_brl = item_total_brl + freight_total_brl
3. difference_brl = total_payment_brl - expected_total_brl
4. is_reconciled = abs(difference_brl) <= 0.10
5. is_split_payment = (number of payment rows >= 2)

Respond with JSON:
{{
  "payments_count": <int>,
  "total_payment_brl": <float, 2 decimal places>,
  "item_total_brl": <float>,
  "freight_total_brl": <float>,
  "expected_total_brl": <float>,
  "difference_brl": <float>,
  "is_reconciled": <true/false>,
  "is_split_payment": <true/false>,
  "payment_ids": ["<order_id>:<payment_sequential>", ...],
  "reasoning": "<brief explanation>"
}}"""

    logger.info(f"[{case_id}] PaymentAgent: Calling LLM...")
    result = call_llm_json(SYSTEM_PROMPT, user_prompt)
    logger.info(f"[{case_id}] PaymentAgent: payments={result.get('payments_count')}, reconciled={result.get('is_reconciled')}")

    context["payment_analysis"] = result
    return context
