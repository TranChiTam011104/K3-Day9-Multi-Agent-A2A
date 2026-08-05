"""
Confidence Calculator Module
Tính confidence dựa trên evidence từ các agents trong hệ thống multi-agent.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_order_agent_confidence(order_data: Dict[str, Any]) -> float:
    """
    Order & Seller Agent: Tính confidence dựa trên order data availability.
    
    Evidence quality factors:
    - Order exists and has valid status
    - Has items associated
    - Has seller info
    """
    if "error" in order_data:
        return 0.0
    
    order = order_data.get("order", {})
    items_count = order_data.get("items_count", 0)
    seller_count = len(order_data.get("seller_ids", []))
    
    # Base confidence from data completeness
    confidence = 0.8
    
    # Boost for having items
    if items_count > 0:
        confidence += 0.1
    
    # Boost for having seller info
    if seller_count > 0:
        confidence += 0.1
    
    # Order status must be valid
    order_status = order.get("order_status", "")
    if order_status in ["canceled", "unavailable", "delivered"]:
        confidence += 0.0  # Already have base, these are deterministic cases
    
    return min(1.0, confidence)


def calculate_payment_agent_confidence(payment_data: Dict[str, Any]) -> float:
    """
    Payment Agent: Tính confidence dựa trên payment reconciliation quality.
    
    Evidence quality factors:
    - Payment is reconciled (within tolerance)
    - Multiple payment types increase confidence
    - Perfect reconciliation (difference = 0) is highest confidence
    """
    if "error" in payment_data:
        return 0.0
    
    payments_count = payment_data.get("payments_count", 0)
    is_reconciled = payment_data.get("is_reconciled", False)
    difference = abs(payment_data.get("difference_brl", 0))
    
    # Base confidence
    confidence = 0.85
    
    # Perfect reconciliation is highest confidence
    if difference == 0:
        confidence = 1.0
    elif difference <= 0.01:
        confidence = 0.98
    elif difference <= 0.05:
        confidence = 0.95
    
    # Split payment adds confidence
    if payments_count >= 2 and is_reconciled:
        confidence = min(1.0, confidence + 0.02)
    
    return confidence


def calculate_delivery_agent_confidence(delivery_data: Dict[str, Any]) -> float:
    """
    Delivery Agent: Tính confidence dựa trên delivery timing evidence.
    
    Evidence quality factors:
    - All required dates are present
    - Clear determination of late/on-time
    - Seller handoff evidence
    """
    if "error" in delivery_data:
        return 0.0
    
    # Check date completeness
    has_estimated = delivery_data.get("estimated_delivery") is not None
    has_delivered = delivery_data.get("delivered_customer") is not None
    has_carrier = delivery_data.get("delivered_carrier") is not None
    
    # Base confidence
    confidence = 0.85
    
    # Boost for complete dates
    if has_estimated and has_delivered:
        confidence += 0.05  # Can determine late/on-time
    
    if has_carrier:
        confidence += 0.05  # Can determine seller responsibility
    
    # Shipping limits availability
    shipping_limits = delivery_data.get("shipping_limits", [])
    if shipping_limits:
        confidence += 0.05  # Can compare with shipping limit
    
    return min(1.0, confidence)


def calculate_cross_agent_confidence(
    order_confidence: float,
    payment_confidence: float,
    delivery_confidence: float,
    policy_match_quality: float = 1.0,
) -> float:
    """
    Policy Agent: Tính tổng confidence dựa trên tất cả agents.
    
    Cross-agent validation increases confidence when multiple agents
    agree on the assessment.
    
    Args:
        order_confidence: Confidence từ Order & Seller Agent
        payment_confidence: Confidence từ Payment Agent
        delivery_confidence: Confidence từ Delivery Agent
        policy_match_quality: Quality of policy match (0.0 - 1.0)
    
    Returns:
        Combined confidence score
    """
    # Weights for each agent
    weights = {
        "order": 0.25,
        "payment": 0.25,
        "delivery": 0.30,  # Delivery is key for late delivery cases
        "policy": 0.20,
    }
    
    # Weighted average
    base_confidence = (
        weights["order"] * order_confidence +
        weights["payment"] * payment_confidence +
        weights["delivery"] * delivery_confidence +
        weights["policy"] * policy_match_quality
    )
    
    # Boost for cross-agent agreement (all agents have high confidence)
    min_confidence = min(order_confidence, payment_confidence, delivery_confidence)
    if min_confidence >= 0.9:
        base_confidence = min(1.0, base_confidence * 1.05)
    
    return round(min(1.0, base_confidence), 2)


def calculate_policy_confidence(
    primary_issue: str,
    order_data: Dict[str, Any],
    payment_data: Dict[str, Any],
    delivery_data: Dict[str, Any],
) -> float:
    """
    Calculate final confidence for a policy decision based on all agent outputs.
    
    Args:
        primary_issue: The determined primary issue
        order_data: Output from Order & Seller Agent
        payment_data: Output from Payment Agent
        delivery_data: Output from Delivery Agent
    
    Returns:
        Final confidence score
    """
    # Get individual agent confidences
    order_conf = calculate_order_agent_confidence(order_data)
    payment_conf = calculate_payment_agent_confidence(payment_data)
    delivery_conf = calculate_delivery_agent_confidence(delivery_data)
    
    # Policy-specific adjustments
    policy_match_quality = 1.0
    
    # For deterministic issues (canceled/unavailable), we can be very confident
    # These cases are clear-cut - order status alone is definitive
    if primary_issue in ["canceled_order_paid", "unavailable_order_paid"]:
        if order_data.get("order", {}).get("order_status") in ["canceled", "unavailable"]:
            policy_match_quality = 1.0
            # For deterministic cases, return max confidence
            return 1.0
        else:
            policy_match_quality = 0.5
    
    # For late delivery cases, delivery evidence is critical
    elif primary_issue in ["late_delivery_seller", "late_delivery_logistics"]:
        if delivery_data.get("is_late_delivery"):
            policy_match_quality = 0.95
        else:
            policy_match_quality = 0.3  # Contradicting evidence
    
    # For payment-related cases
    elif primary_issue in ["valid_split_payment", "unsupported_late_claim"]:
        if payment_data.get("is_reconciled"):
            policy_match_quality = 0.95
        else:
            policy_match_quality = 0.5
    
    # Calculate cross-agent confidence
    final_confidence = calculate_cross_agent_confidence(
        order_confidence=order_conf,
        payment_confidence=payment_conf,
        delivery_confidence=delivery_conf,
        policy_match_quality=policy_match_quality,
    )
    
    logger.debug(
        f"Confidence breakdown: order={order_conf:.2f}, "
        f"payment={payment_conf:.2f}, delivery={delivery_conf:.2f}, "
        f"policy={policy_match_quality:.2f} -> final={final_confidence:.2f}"
    )
    
    return final_confidence
