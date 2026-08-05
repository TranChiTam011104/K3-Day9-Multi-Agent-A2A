"""
Order & Seller Agent
LLM phân tích trạng thái đơn hàng và thông tin seller.
Nhiệm vụ:
- Kiểm tra order_status (canceled, unavailable, delivered, ...)
- Kiểm tra shipping_limit_date vs order_delivered_carrier_date cho từng seller
- Xác định seller nào bàn giao muộn
"""

import logging
from typing import Dict, Any, List

from src.llm_client import call_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an Order & Seller Analyst Agent for an e-commerce dispute resolution system.

You receive raw data extracted from the Olist Brazilian e-commerce database about a specific order.
Your job is to:
1. Identify the order status
2. For each seller in the order, determine if they handed off the parcel AFTER their shipping_limit_date
   - Compare order_delivered_carrier_date with each item's shipping_limit_date
   - A seller is "late" if order_delivered_carrier_date > shipping_limit_date (string comparison is valid since dates are ISO format)
   - A seller is "on_time" if order_delivered_carrier_date <= shipping_limit_date
   - If order_delivered_carrier_date is null/NaN, seller cannot be classified (treat as on_time)

You must respond with a valid JSON object only, no extra text.
"""

def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chạy Order & Seller Agent.

    Args:
        context: Dict chứa order_data từ data_loader

    Returns:
        Context được bổ sung kết quả phân tích order/seller
    """
    order_data = context["order_data"]
    case_id = context["case_id"]
    order_id = context["order_id"]

    order = order_data.get("order", {})
    items = order_data.get("items", [])

    # Build item/seller summary for LLM
    seller_items = []
    for item in items:
        seller_items.append({
            "order_item_id": item.get("order_item_id"),
            "seller_id": item.get("seller_id"),
            "shipping_limit_date": str(item.get("shipping_limit_date", "")),
        })

    user_prompt = f"""Analyze this order and determine seller handoff compliance:

Order ID: {order_id}
Order Status: {order.get("order_status", "unknown")}
Order Delivered Carrier Date: {order.get("order_delivered_carrier_date", "null")}
Order Approved At: {order.get("order_approved_at", "null")}

Items/Sellers:
{seller_items}

Based on this data, classify each seller as "late" or "on_time" by comparing order_delivered_carrier_date vs each item's shipping_limit_date.

Respond with JSON:
{{
  "order_status": "<status string>",
  "delivered_carrier_date": "<date string or null>",
  "late_sellers": ["<seller_id>", ...],
  "on_time_sellers": ["<seller_id>", ...],
  "all_seller_ids": ["<seller_id>", ...],
  "reasoning": "<brief explanation>"
}}"""

    logger.info(f"[{case_id}] OrderSellerAgent: Calling LLM...")
    result = call_llm_json(SYSTEM_PROMPT, user_prompt)
    logger.info(f"[{case_id}] OrderSellerAgent: status={result.get('order_status')}, late_sellers={result.get('late_sellers')}")

    context["order_seller_analysis"] = result
    return context
