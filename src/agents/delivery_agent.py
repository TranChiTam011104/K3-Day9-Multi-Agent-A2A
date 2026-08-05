"""
Delivery Agent
LLM phân tích timing giao hàng.
Nhiệm vụ:
- So sánh order_delivered_customer_date vs order_estimated_delivery_date
- Xác định đơn có bị giao trễ hay không
"""

import logging
from typing import Dict, Any

from src.llm_client import call_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Delivery Timing Analyst Agent for an e-commerce dispute resolution system.

You receive order dates from the Olist database.
Your job is to:
1. Compare order_delivered_customer_date with order_estimated_delivery_date
2. Determine if the delivery was late: delivered_customer_date > estimated_delivery_date
3. If either date is null/NaN/missing, delivery cannot be assessed as late

Important rules:
- Date strings are in ISO format (YYYY-MM-DD HH:MM:SS), direct string comparison works correctly
- If the order was NOT delivered (no delivered_customer_date), do NOT mark as late
- Only mark as late if actual delivery happened AND it was after estimated date

You must respond with a valid JSON object only, no extra text.
"""

def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chạy Delivery Agent.

    Args:
        context: Dict chứa order_data và kết quả từ các agent trước

    Returns:
        Context được bổ sung kết quả phân tích delivery timing
    """
    order_data = context["order_data"]
    case_id = context["case_id"]

    order = order_data.get("order", {})

    estimated_delivery = order.get("order_estimated_delivery_date")
    delivered_customer = order.get("order_delivered_customer_date")
    order_status = order.get("order_status", "unknown")

    user_prompt = f"""Analyze delivery timing for this order:

Order Status: {order_status}
Estimated Delivery Date: {estimated_delivery or "null"}
Actual Delivered to Customer Date: {delivered_customer or "null"}

Determine if the delivery was late.

Respond with JSON:
{{
  "estimated_delivery_date": "<date string or null>",
  "delivered_customer_date": "<date string or null>",
  "is_late_delivery": <true/false>,
  "days_late": <number or null if cannot compute>,
  "reasoning": "<brief explanation>"
}}"""

    logger.info(f"[{case_id}] DeliveryAgent: Calling LLM...")
    result = call_llm_json(SYSTEM_PROMPT, user_prompt)
    logger.info(f"[{case_id}] DeliveryAgent: is_late={result.get('is_late_delivery')}")

    context["delivery_analysis"] = result
    return context
