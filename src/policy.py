"""
Policy Module
EC_POLICY_V1 business rules implementation.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Constants
OLIST_PLATFORM = "OLIST_PLATFORM"
LOGISTICS_PROVIDER = "LOGISTICS_PROVIDER"


class PrimaryIssue(Enum):
    CANCELED_ORDER_PAID = "canceled_order_paid"
    UNAVAILABLE_ORDER_PAID = "unavailable_order_paid"
    LATE_DELIVERY_SELLER = "late_delivery_seller"
    LATE_DELIVERY_LOGISTICS = "late_delivery_logistics"
    VALID_SPLIT_PAYMENT = "valid_split_payment"
    UNSUPPORTED_LATE_CLAIM = "unsupported_late_claim"


class RootCauseCode(Enum):
    SELLER_HANDOFF_AFTER_LIMIT = "SELLER_HANDOFF_AFTER_LIMIT"
    CARRIER_DELIVERED_AFTER_ESTIMATE = "CARRIER_DELIVERED_AFTER_ESTIMATE"
    ORDER_CANCELED_AFTER_PAYMENT = "ORDER_CANCELED_AFTER_PAYMENT"
    ORDER_UNAVAILABLE_AFTER_PAYMENT = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
    MULTIPLE_PAYMENTS_RECONCILED = "MULTIPLE_PAYMENTS_RECONCILED"
    DELIVERY_WITHIN_ESTIMATE = "DELIVERY_WITHIN_ESTIMATE"


class ResolutionAction(Enum):
    ISSUE_FULL_REFUND = "issue_full_refund"
    REFUND_FREIGHT = "refund_freight"
    EXPLAIN_VALID_SPLIT_PAYMENT = "explain_valid_split_payment"
    REJECT_LATE_REFUND = "reject_late_refund"


@dataclass
class PolicyResult:
    primary_issue: str
    case_status: str
    confidence: float
    responsible_parties: List[Dict[str, str]]
    root_cause_codes: List[Dict[str, Any]]
    recommended_refund_brl: float
    resolution_actions: List[str]


def check_canceled_order_paid(order_status: str, payment_total: float) -> Optional[PolicyResult]:
    """
    Kiß╗âm tra ─æiß╗üu kiß╗çn: order canceled v├á ─æ├ú thanh to├ín.

    Args:
        order_status: Trß║íng th├íi ─æ╞ín h├áng
        payment_total: Tß╗òng tiß╗ün thanh to├ín

    Returns:
        PolicyResult nß║┐u match, None otherwise
    """
    if order_status == "canceled" and payment_total > 0:
        return PolicyResult(
            primary_issue=PrimaryIssue.CANCELED_ORDER_PAID.value,
            case_status="action_required",
            confidence=1.0,
            responsible_parties=[
                {"party_type": "platform", "party_id": OLIST_PLATFORM}
            ],
            root_cause_codes=[
                {"cause_code": RootCauseCode.ORDER_CANCELED_AFTER_PAYMENT.value, "rank": 1}
            ],
            recommended_refund_brl=round(payment_total, 2),
            resolution_actions=[ResolutionAction.ISSUE_FULL_REFUND.value],
        )
    return None


def check_unavailable_order_paid(order_status: str, payment_total: float) -> Optional[PolicyResult]:
    """
    Kiß╗âm tra ─æiß╗üu kiß╗çn: order unavailable v├á ─æ├ú thanh to├ín.

    Args:
        order_status: Trß║íng th├íi ─æ╞ín h├áng
        payment_total: Tß╗òng tiß╗ün thanh to├ín

    Returns:
        PolicyResult nß║┐u match, None otherwise
    """
    if order_status == "unavailable" and payment_total > 0:
        return PolicyResult(
            primary_issue=PrimaryIssue.UNAVAILABLE_ORDER_PAID.value,
            case_status="action_required",
            confidence=1.0,
            responsible_parties=[
                {"party_type": "platform", "party_id": OLIST_PLATFORM}
            ],
            root_cause_codes=[
                {"cause_code": RootCauseCode.ORDER_UNAVAILABLE_AFTER_PAYMENT.value, "rank": 1}
            ],
            recommended_refund_brl=round(payment_total, 2),
            resolution_actions=[ResolutionAction.ISSUE_FULL_REFUND.value],
        )
    return None


def check_late_delivery_seller(
    is_late_delivery: bool,
    late_sellers: List[str],
    freight_total: float,
) -> Optional[PolicyResult]:
    """
    Kiß╗âm tra ─æiß╗üu kiß╗çn: giao trß╗à do seller b├án giao muß╗Ön.

    Args:
        is_late_delivery: Giao c├│ trß╗à kh├┤ng
        late_sellers: Danh s├ích seller b├án giao muß╗Ön
        freight_total: Tß╗òng tiß╗ün freight

    Returns:
        PolicyResult nß║┐u match, None otherwise
    """
    if is_late_delivery and late_sellers:
        # Filter out empty strings
        valid_sellers = [s for s in late_sellers if s]
        if valid_sellers:
            return PolicyResult(
                primary_issue=PrimaryIssue.LATE_DELIVERY_SELLER.value,
                case_status="action_required",
                confidence=0.92,
                responsible_parties=[
                    {"party_type": "seller", "party_id": seller_id}
                    for seller_id in valid_sellers
                ],
                root_cause_codes=[
                    {"cause_code": RootCauseCode.SELLER_HANDOFF_AFTER_LIMIT.value, "rank": 1}
                ],
                recommended_refund_brl=round(freight_total, 2),
                resolution_actions=[ResolutionAction.REFUND_FREIGHT.value],
            )
    return None


def check_late_delivery_logistics(
    is_late_delivery: bool,
    late_sellers: List[str],
    on_time_sellers: List[str],
    freight_total: float,
) -> Optional[PolicyResult]:
    """
    Kiß╗âm tra ─æiß╗üu kiß╗çn: giao trß╗à do logistics, kh├┤ng phß║úi seller.

    Args:
        is_late_delivery: Giao c├│ trß╗à kh├┤ng
        late_sellers: Danh s├ích seller b├án giao muß╗Ön
        on_time_sellers: Danh s├ích seller b├án giao ─æ├║ng hß║ín
        freight_total: Tß╗òng tiß╗ün freight

    Returns:
        PolicyResult nß║┐u match, None otherwise
    """
    # Logistics responsible if: delivery late AND all sellers handed off on time
    if is_late_delivery:
        # Check if ALL sellers are on time (no late sellers)
        valid_late = [s for s in late_sellers if s]
        valid_on_time = [s for s in on_time_sellers if s]

        if len(valid_late) == 0 and len(valid_on_time) > 0:
            return PolicyResult(
                primary_issue=PrimaryIssue.LATE_DELIVERY_LOGISTICS.value,
                case_status="action_required",
                confidence=0.88,
                responsible_parties=[
                    {"party_type": "logistics_provider", "party_id": LOGISTICS_PROVIDER}
                ],
                root_cause_codes=[
                    {"cause_code": RootCauseCode.CARRIER_DELIVERED_AFTER_ESTIMATE.value, "rank": 1}
                ],
                recommended_refund_brl=round(freight_total, 2),
                resolution_actions=[ResolutionAction.REFUND_FREIGHT.value],
            )
    return None


def check_valid_split_payment(
    payments_count: int,
    is_reconciled: bool,
    payment_total: float,
) -> Optional[PolicyResult]:
    """
    Kiß╗âm tra ─æiß╗üu kiß╗çn: split payment hß╗úp lß╗ç.

    Args:
        payments_count: Sß╗æ l╞░ß╗úng payment rows
        is_reconciled: Payment c├│ khß╗¢p vß╗¢i item + freight kh├┤ng
        payment_total: Tß╗òng tiß╗ün payment

    Returns:
        PolicyResult nß║┐u match, None otherwise
    """
    if payments_count >= 2 and is_reconciled:
        return PolicyResult(
            primary_issue=PrimaryIssue.VALID_SPLIT_PAYMENT.value,
            case_status="no_action",
            confidence=0.95,
            responsible_parties=[],
            root_cause_codes=[
                {"cause_code": RootCauseCode.MULTIPLE_PAYMENTS_RECONCILED.value, "rank": 1}
            ],
            recommended_refund_brl=0.0,
            resolution_actions=[ResolutionAction.EXPLAIN_VALID_SPLIT_PAYMENT.value],
        )
    return None


def check_unsupported_late_claim(
    is_late_delivery: bool,
    is_reconciled: bool,
    payment_total: float,
) -> Optional[PolicyResult]:
    """
    Kiß╗âm tra ─æiß╗üu kiß╗çn: khiß║┐u nß║íi giao trß╗à kh├┤ng ─æ╞░ß╗úc hß╗ù trß╗ú.

    Args:
        is_late_delivery: Giao c├│ trß╗à kh├┤ng
        is_reconciled: Payment c├│ khß╗¢p vß╗¢i item + freight kh├┤ng
        payment_total: Tß╗òng tiß╗ün payment

    Returns:
        PolicyResult nß║┐u match, None otherwise
    """
    # Late claim not supported if: delivery on time AND payment matches
    if not is_late_delivery and is_reconciled:
        return PolicyResult(
            primary_issue=PrimaryIssue.UNSUPPORTED_LATE_CLAIM.value,
            case_status="no_action",
            confidence=0.90,
            responsible_parties=[],
            root_cause_codes=[
                {"cause_code": RootCauseCode.DELIVERY_WITHIN_ESTIMATE.value, "rank": 1}
            ],
            recommended_refund_brl=0.0,
            resolution_actions=[ResolutionAction.REJECT_LATE_REFUND.value],
        )
    return None


def apply_policy(
    order_status: str,
    payment_total: float,
    is_late_delivery: bool,
    late_sellers: List[str],
    on_time_sellers: List[str],
    payments_count: int,
    is_reconciled: bool,
    freight_total: float,
) -> PolicyResult:
    """
    ├üp dß╗Ñng EC_POLICY_V1 theo thß╗⌐ tß╗▒ ╞░u ti├¬n.

    Priority:
    1. canceled_order_paid
    2. unavailable_order_paid
    3. late_delivery_seller
    4. late_delivery_logistics
    5. valid_split_payment
    6. unsupported_late_claim

    Args:
        order_status: Trß║íng th├íi ─æ╞ín h├áng
        payment_total: Tß╗òng tiß╗ün thanh to├ín
        is_late_delivery: Giao c├│ trß╗à kh├┤ng
        late_sellers: Danh s├ích seller b├án giao muß╗Ön
        on_time_sellers: Danh s├ích seller b├án giao ─æ├║ng hß║ín
        payments_count: Sß╗æ l╞░ß╗úng payment rows
        is_reconciled: Payment c├│ khß╗¢p kh├┤ng
        freight_total: Tß╗òng tiß╗ün freight

    Returns:
        PolicyResult vß╗¢i kß║┐t quß║ú policy
    """
    # Priority 1: canceled_order_paid
    result = check_canceled_order_paid(order_status, payment_total)
    if result:
        return result

    # Priority 2: unavailable_order_paid
    result = check_unavailable_order_paid(order_status, payment_total)
    if result:
        return result

    # Priority 3: late_delivery_seller
    result = check_late_delivery_seller(is_late_delivery, late_sellers, freight_total)
    if result:
        return result

    # Priority 4: late_delivery_logistics
    result = check_late_delivery_logistics(
        is_late_delivery, late_sellers, on_time_sellers, freight_total
    )
    if result:
        return result

    # Priority 5: valid_split_payment
    result = check_valid_split_payment(payments_count, is_reconciled, payment_total)
    if result:
        return result

    # Priority 6: unsupported_late_claim
    result = check_unsupported_late_claim(is_late_delivery, is_reconciled, payment_total)
    if result:
        return result

    # Fallback: should not reach here if all conditions are covered
    return PolicyResult(
        primary_issue="unknown",
        case_status="no_action",
        confidence=0.0,
        responsible_parties=[],
        root_cause_codes=[],
        recommended_refund_brl=0.0,
        resolution_actions=[],
    )
