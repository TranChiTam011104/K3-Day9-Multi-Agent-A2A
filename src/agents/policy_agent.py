"""
Policy Agent
LLM áp dụng EC_POLICY_V1 dựa trên kết quả từ các agent trước.
Nhiệm vụ:
- Nhận evidence từ Order/Seller, Payment, Delivery agents
- Áp dụng policy theo thứ tự ưu tiên
- Xác định primary_issue, responsible_party, refund, action
"""

import logging
from typing import Dict, Any

from src.llm_client import call_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Policy Agent applying EC_POLICY_V1 for e-commerce dispute resolution.

Given evidence from multiple data analysis agents, apply the following business rules IN PRIORITY ORDER:

| Priority | primary_issue             | Condition                                                              | responsible_party_type | responsible_party_id   | refund                | action                        |
|----------|--------------------------|------------------------------------------------------------------------|----------------------|----------------------|-----------------------|-------------------------------|
| 1        | canceled_order_paid      | order_status = 'canceled' AND payment_total > 0                       | platform              | OLIST_PLATFORM        | total_payment_brl     | issue_full_refund             |
| 2        | unavailable_order_paid   | order_status = 'unavailable' AND payment_total > 0                    | platform              | OLIST_PLATFORM        | total_payment_brl     | issue_full_refund             |
| 3        | late_delivery_seller     | is_late_delivery=true AND late_sellers list is NOT empty              | seller                | <seller_id>           | freight_total_brl     | refund_freight                |
| 4        | late_delivery_logistics  | is_late_delivery=true AND late_sellers is empty AND on_time_sellers not empty | logistics_provider | LOGISTICS_PROVIDER   | freight_total_brl     | refund_freight                |
| 5        | valid_split_payment      | payments_count >= 2 AND is_reconciled=true                           | none                  | none                  | 0                     | explain_valid_split_payment   |
| 6        | unsupported_late_claim   | is_late_delivery=false AND is_reconciled=true                        | none                  | none                  | 0                     | reject_late_refund            |

ROOT CAUSE CODES mapping:
- canceled_order_paid → ORDER_CANCELED_AFTER_PAYMENT
- unavailable_order_paid → ORDER_UNAVAILABLE_AFTER_PAYMENT
- late_delivery_seller → SELLER_HANDOFF_AFTER_LIMIT
- late_delivery_logistics → CARRIER_DELIVERED_AFTER_ESTIMATE
- valid_split_payment → MULTIPLE_PAYMENTS_RECONCILED
- unsupported_late_claim → DELIVERY_WITHIN_ESTIMATE

case_status:
- "action_required" if recommended_refund_brl > 0
- "no_action" if recommended_refund_brl = 0

Confidence levels:
- canceled/unavailable: 1.0
- late_delivery_seller: 0.92
- late_delivery_logistics: 0.88
- valid_split_payment: 0.95
- unsupported_late_claim: 0.90

CRITICAL: Apply rules in STRICT PRIORITY ORDER. Stop at the FIRST matching rule.
All monetary amounts must be rounded to 2 decimal places.
You must respond with a valid JSON object only.
"""

def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chạy Policy Agent.

    Args:
        context: Dict chứa kết quả từ tất cả các agents trước

    Returns:
        Context được bổ sung kết quả policy
    """
    case_id = context["case_id"]
    order_seller = context["order_seller_analysis"]
    payment = context["payment_analysis"]
    delivery = context["delivery_analysis"]

    user_prompt = f"""Apply EC_POLICY_V1 to determine the dispute resolution for this case.

=== Evidence from Order & Seller Agent ===
order_status: {order_seller.get('order_status')}
late_sellers: {order_seller.get('late_sellers', [])}
on_time_sellers: {order_seller.get('on_time_sellers', [])}

=== Evidence from Payment Agent ===
payments_count: {payment.get('payments_count')}
total_payment_brl: {payment.get('total_payment_brl')}
freight_total_brl: {payment.get('freight_total_brl')}
item_total_brl: {payment.get('item_total_brl')}
is_reconciled: {payment.get('is_reconciled')}
is_split_payment: {payment.get('is_split_payment')}

=== Evidence from Delivery Agent ===
is_late_delivery: {delivery.get('is_late_delivery')}
delivered_customer_date: {delivery.get('delivered_customer_date')}
estimated_delivery_date: {delivery.get('estimated_delivery_date')}

Now apply the policy rules in strict priority order and return the result.
For late_delivery_seller, use the FIRST seller from late_sellers list as the primary responsible party.

Respond with JSON:
{{
  "primary_issue": "<one of the 6 issue codes>",
  "case_status": "<action_required or no_action>",
  "confidence": <float 0-1>,
  "responsible_party_type": "<platform|seller|logistics_provider|none>",
  "responsible_party_id": "<OLIST_PLATFORM|LOGISTICS_PROVIDER|seller_id|none>",
  "root_cause_code": "<one of the 6 root cause codes>",
  "recommended_refund_brl": <float, 2 decimal places>,
  "resolution_action": "<one action string>",
  "reasoning": "<step-by-step explanation of which rule matched and why>"
}}"""

    logger.info(f"[{case_id}] PolicyAgent: Calling LLM...")
    result = call_llm_json(SYSTEM_PROMPT, user_prompt)
    logger.info(f"[{case_id}] PolicyAgent: primary_issue={result.get('primary_issue')}, refund={result.get('recommended_refund_brl')}")

    context["policy_result"] = result
    return context
