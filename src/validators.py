"""
Validators Module
Validate output schema và evidence IDs.
"""

import re
from typing import Dict, Any, List, Tuple
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Evidence ID patterns
EVIDENCE_PATTERNS = {
    "order": r"^order:[a-zA-Z0-9]+$",
    "item": r"^item:[a-zA-Z0-9]+:\d+$",
    "payment": r"^payment:[a-zA-Z0-9]+:\d+$",
    "seller": r"^seller:[a-zA-Z0-9]+$",
    "policy": r"^policy:[A-Z_]+$",
}

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

# Valid responsible parties
VALID_PARTY_TYPES = {"platform", "seller", "logistics_provider", "customer"}

# Valid resolution actions
VALID_RESOLUTION_ACTIONS = {
    "issue_full_refund",
    "refund_freight",
    "explain_valid_split_payment",
    "reject_late_refund",
}


def validate_evidence_id(evidence_id: str) -> Tuple[bool, str]:
    """
    Validate một evidence ID.

    Args:
        evidence_id: Evidence ID cần validate

    Returns:
        (is_valid, error_message)
    """
    if not evidence_id:
        return False, "Evidence ID is empty"

    # Check pattern
    valid_pattern = False
    for prefix, pattern in EVIDENCE_PATTERNS.items():
        if re.match(pattern, evidence_id):
            valid_pattern = True
            break

    if not valid_pattern:
        return False, f"Invalid evidence ID format: {evidence_id}"

    # For policy evidence, check if root cause code is valid
    if evidence_id.startswith("policy:"):
        code = evidence_id.split(":")[1]
        if code not in VALID_ROOT_CAUSE_CODES:
            return False, f"Invalid root cause code: {code}"

    return True, ""


def validate_evidence_ids(evidence_ids: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate danh sách evidence IDs.

    Args:
        evidence_ids: List các evidence IDs

    Returns:
        (all_valid, list_of_errors)
    """
    errors = []
    for eid in evidence_ids:
        valid, err = validate_evidence_id(eid)
        if not valid:
            errors.append(err)
    return len(errors) == 0, errors


def verify_evidence_exists_in_csv(
    evidence_id: str, data_cache: Dict[str, pd.DataFrame]
) -> Tuple[bool, str]:
    """
    Verify evidence ID có tồn tại trong CSV data.

    Args:
        evidence_id: Evidence ID cần verify
        data_cache: Dict của DataFrames

    Returns:
        (exists, message)
    """
    if evidence_id.startswith("order:"):
        order_id = evidence_id.split(":")[1]
        orders = data_cache.get("olist_orders_dataset.csv")
        if orders is not None and not orders.empty:
            if order_id in orders["order_id"].values:
                return True, f"Order {order_id} exists"
            return False, f"Order {order_id} not found in orders.csv"
        return False, "orders.csv not loaded"

    elif evidence_id.startswith("item:"):
        parts = evidence_id.split(":")
        order_id, item_id = parts[1], int(parts[2])
        items = data_cache.get("olist_order_items_dataset.csv")
        if items is not None and not items.empty:
            match = items[
                (items["order_id"] == order_id) & (items["order_item_id"] == item_id)
            ]
            if not match.empty:
                return True, f"Item {order_id}:{item_id} exists"
            return False, f"Item {order_id}:{item_id} not found"
        return False, "order_items.csv not loaded"

    elif evidence_id.startswith("payment:"):
        parts = evidence_id.split(":")
        order_id, seq = parts[1], int(parts[2])
        payments = data_cache.get("olist_order_payments_dataset.csv")
        if payments is not None and not payments.empty:
            match = payments[
                (payments["order_id"] == order_id)
                & (payments["payment_sequential"] == seq)
            ]
            if not match.empty:
                return True, f"Payment {order_id}:{seq} exists"
            return False, f"Payment {order_id}:{seq} not found"
        return False, "order_payments.csv not loaded"

    elif evidence_id.startswith("seller:"):
        seller_id = evidence_id.split(":")[1]
        sellers = data_cache.get("olist_sellers_dataset.csv")
        if sellers is not None and not sellers.empty:
            if seller_id in sellers["seller_id"].values:
                return True, f"Seller {seller_id} exists"
            return False, f"Seller {seller_id} not found"
        return False, "sellers.csv not loaded"

    elif evidence_id.startswith("policy:"):
        # Policy IDs don't need CSV verification
        return True, "Policy evidence"

    return False, "Unknown evidence type"


def validate_output_schema(output: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate toàn bộ output schema.

    Args:
        output: Output dict cần validate

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Check required top-level keys
    required_keys = [
        "case_id",
        "assessment",
        "affected_entities",
        "root_cause_analysis",
        "evidence_ids",
        "financial_resolution",
        "resolution_actions",
    ]

    for key in required_keys:
        if key not in output:
            errors.append(f"Missing required key: {key}")

    if "case_id" in output:
        if not re.match(r"^EC_\d{3}$", output["case_id"]):
            errors.append(f"Invalid case_id format: {output['case_id']}")

    # Validate assessment
    if "assessment" in output:
        assessment = output["assessment"]
        if "primary_issue" in assessment:
            if assessment["primary_issue"] not in VALID_PRIMARY_ISSUES:
                errors.append(
                    f"Invalid primary_issue: {assessment['primary_issue']}"
                )
        if "case_status" in assessment:
            if assessment["case_status"] not in ["action_required", "no_action"]:
                errors.append(
                    f"Invalid case_status: {assessment['case_status']}"
                )
        if "confidence" in assessment:
            conf = assessment["confidence"]
            if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
                errors.append(f"Invalid confidence: {conf} (must be 0-1)")

    # Validate affected_entities limits
    if "affected_entities" in output:
        entities = output["affected_entities"]
        limits = {
            "order_ids": 5,
            "item_ids": 5,
            "seller_ids": 5,
            "payment_ids": 5,
        }
        for field, limit in limits.items():
            if field in entities and len(entities[field]) > limit:
                errors.append(
                    f"{field} exceeds limit of {limit}: {len(entities[field])}"
                )

    # Validate evidence_ids limits and format
    if "evidence_ids" in output:
        eids = output["evidence_ids"]
        if len(eids) > 10:
            errors.append(f"evidence_ids exceeds limit of 10: {len(eids)}")

        valid, errs = validate_evidence_ids(eids)
        if not valid:
            errors.extend(errs)

    # Validate root_cause_analysis
    if "root_cause_analysis" in output:
        rca = output["root_cause_analysis"]
        if "ranked_causes" in rca:
            if len(rca["ranked_causes"]) > 3:
                errors.append(
                    f"ranked_causes exceeds limit of 3: {len(rca['ranked_causes'])}"
                )
        if "responsible_parties" in rca:
            if len(rca["responsible_parties"]) > 3:
                errors.append(
                    f"responsible_parties exceeds limit of 3: {len(rca['responsible_parties'])}"
                )

    # Validate financial_resolution
    if "financial_resolution" in output:
        fin = output["financial_resolution"]
        if "currency" in fin and fin["currency"] != "BRL":
            errors.append(f"Invalid currency: {fin['currency']} (must be BRL)")
        if "recommended_refund_brl" in fin:
            refund = fin["recommended_refund_brl"]
            if not isinstance(refund, (int, float)) or refund < 0:
                errors.append(f"Invalid refund amount: {refund}")

    # Validate resolution_actions
    if "resolution_actions" in output:
        actions = output["resolution_actions"]
        if len(actions) > 5:
            errors.append(f"resolution_actions exceeds limit of 5: {len(actions)}")
        for action in actions:
            if action not in VALID_RESOLUTION_ACTIONS:
                errors.append(f"Invalid resolution_action: {action}")

    return len(errors) == 0, errors


def validate_financial_totals(
    item_total: float, freight_total: float, payment_total: float, tolerance: float = 0.10
) -> Tuple[bool, float]:
    """
    Validate financial totals are consistent.

    Args:
        item_total: Tổng tiền items
        freight_total: Tổng tiền freight
        payment_total: Tổng tiền payment
        tolerance: Sai số cho phép

    Returns:
        (is_valid, difference)
    """
    expected = round(item_total + freight_total, 2)
    difference = round(payment_total - expected, 2)
    is_valid = abs(difference) <= tolerance
    return is_valid, difference
