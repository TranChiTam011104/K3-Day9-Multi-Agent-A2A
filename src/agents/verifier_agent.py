"""
Verifier Agent
LLM validate output schema và evidence IDs trước khi ghi file.
Nhiệm vụ:
- Validate format evidence IDs
- Đảm bảo giới hạn: max 10 evidence, 5 entity IDs mỗi loại, 3 causes, 5 actions
- Validate financial amounts
- Đảm bảo required fields đều có mặt
"""

import logging
from typing import Dict, Any, List

from src.llm_client import call_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Verifier Agent for an e-commerce dispute resolution system.

You receive a draft output JSON and must:
1. Validate that all required fields are present
2. Enforce limits:
   - order_ids: max 5
   - item_ids: max 5  
   - seller_ids: max 5
   - payment_ids: max 5
   - evidence_ids: max 10
   - ranked_causes: max 3
   - responsible_parties: max 3
   - resolution_actions: max 5
3. Validate evidence ID formats:
   - order:<order_id>
   - item:<order_id>:<order_item_id>
   - payment:<order_id>:<payment_sequential>
   - seller:<seller_id>
   - policy:<ROOT_CAUSE_CODE>
4. Validate confidence is in [0, 1]
5. Validate case_status is "action_required" or "no_action"
6. Validate currency is "BRL"
7. If recommended_refund_brl > 0, case_status must be "action_required"
8. If recommended_refund_brl = 0, case_status must be "no_action"

Fix any issues and return a clean, valid output JSON.
You must respond with the corrected/verified JSON object only.
"""

# Valid root cause codes
VALID_ROOT_CAUSE_CODES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}

# Valid primary issues
VALID_PRIMARY_ISSUES = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
}

# Valid resolution actions
VALID_RESOLUTION_ACTIONS = {
    "issue_full_refund",
    "refund_freight",
    "explain_valid_split_payment",
    "reject_late_refund",
}


def build_draft_output(context: Dict[str, Any]) -> Dict[str, Any]:
    """Xây dựng draft output từ context."""
    case_id = context["case_id"]
    order_id = context["order_id"]
    order_data = context["order_data"]
    order_seller = context["order_seller_analysis"]
    payment = context["payment_analysis"]
    policy = context["policy_result"]

    items = order_data.get("items", [])
    payments_raw = order_data.get("payments", [])

    # Build item_ids
    item_ids = [f"{order_id}:{item.get('order_item_id', 1)}" for item in items[:5]]

    # Build seller_ids - from policy result first, then order_seller
    seller_ids = order_seller.get("all_seller_ids", order_seller.get("late_sellers", []))
    if not seller_ids:
        seller_ids = order_seller.get("on_time_sellers", [])
    seller_ids = list(dict.fromkeys(seller_ids))[:5]  # deduplicate, max 5

    # Build payment_ids
    payment_ids = [f"{order_id}:{p.get('payment_sequential', i+1)}" for i, p in enumerate(payments_raw[:5])]

    # Build evidence_ids
    evidence_ids = [f"order:{order_id}"]
    for iid in item_ids[:4]:
        evidence_ids.append(f"item:{iid}")
    for pid in payment_ids[:2]:
        evidence_ids.append(f"payment:{pid}")
    for sid in seller_ids[:2]:
        evidence_ids.append(f"seller:{sid}")
    root_cause = policy.get("root_cause_code", "")
    if root_cause:
        evidence_ids.append(f"policy:{root_cause}")
    evidence_ids = list(dict.fromkeys(evidence_ids))[:10]  # deduplicate, max 10

    # Build responsible parties
    party_type = policy.get("responsible_party_type", "none")
    party_id = policy.get("responsible_party_id", "none")
    responsible_parties = []
    if party_type and party_type != "none" and party_id and party_id != "none":
        responsible_parties.append({"party_type": party_type, "party_id": party_id})

    action = policy.get("resolution_action", "")
    resolution_actions = [action] if action else []

    draft = {
        "case_id": case_id,
        "assessment": {
            "primary_issue": policy.get("primary_issue", ""),
            "case_status": policy.get("case_status", "no_action"),
            "confidence": policy.get("confidence", 0.0),
        },
        "affected_entities": {
            "order_ids": [order_id],
            "item_ids": item_ids,
            "seller_ids": seller_ids,
            "payment_ids": payment_ids,
        },
        "root_cause_analysis": {
            "ranked_causes": [{"cause_code": root_cause, "rank": 1}] if root_cause else [],
            "responsible_parties": responsible_parties,
        },
        "evidence_ids": evidence_ids,
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": round(payment.get("item_total_brl", 0.0), 2),
            "freight_total_brl": round(payment.get("freight_total_brl", 0.0), 2),
            "payment_total_brl": round(payment.get("total_payment_brl", 0.0), 2),
            "recommended_refund_brl": round(policy.get("recommended_refund_brl", 0.0), 2),
        },
        "resolution_actions": resolution_actions,
    }
    return draft


def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chạy Verifier Agent.

    Args:
        context: Dict chứa kết quả từ tất cả agents

    Returns:
        Context được bổ sung validated output
    """
    case_id = context["case_id"]

    draft = build_draft_output(context)

    user_prompt = f"""Verify and fix this draft output JSON for case {case_id}:

{draft}

Check and fix:
1. All required fields present
2. All limits enforced (max 10 evidence_ids, max 5 for each entity list, max 3 ranked_causes/responsible_parties, max 5 resolution_actions)
3. Evidence ID formats are correct (order:X, item:X:N, payment:X:N, seller:X, policy:CODE)
4. confidence is in [0, 1]
5. case_status matches refund (action_required if refund > 0, no_action if refund = 0)
6. currency is "BRL"
7. All monetary values rounded to 2 decimal places

Return the complete corrected output JSON (same structure, no extra fields).
The output must be the exact JSON that will be written to file."""

    logger.info(f"[{case_id}] VerifierAgent: Calling LLM...")
    try:
        verified_output = call_llm_json(SYSTEM_PROMPT, user_prompt)
        logger.info(f"[{case_id}] VerifierAgent: Verification complete")
    except Exception as e:
        logger.warning(f"[{case_id}] VerifierAgent: LLM verification failed, using draft: {e}")
        verified_output = draft

    # Final safety checks (deterministic, cannot be hallucinated)
    if "case_id" not in verified_output:
        verified_output["case_id"] = case_id

    # Ensure primary_issue is valid
    if verified_output.get("assessment", {}).get("primary_issue") not in VALID_PRIMARY_ISSUES:
        verified_output.setdefault("assessment", {})["primary_issue"] = draft["assessment"]["primary_issue"]

    # Enforce case_status consistency
    refund = verified_output.get("financial_resolution", {}).get("recommended_refund_brl", 0.0)
    if refund > 0:
        verified_output.setdefault("assessment", {})["case_status"] = "action_required"
    else:
        verified_output.setdefault("assessment", {})["case_status"] = "no_action"

    context["final_output"] = verified_output
    return context
