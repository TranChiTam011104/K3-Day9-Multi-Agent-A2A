"""
Coordinator Agent - Main orchestration script

This script orchestrates the entire multi-agent workflow:
1. Load and preprocess all data
2. Process each case through specialized agents
3. Apply policy rules
4. Generate validated output
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Setup
sys.path.insert(0, str(Path(__file__).parent))
from src import (
    load_all_csvs,
    get_order_with_details,
    analyze_delivery_timing,
    check_payment_reconciliation,
    apply_policy,
    build_output,
    write_output,
    read_input,
    get_case_order_id,
    list_input_cases,
    validate_output_schema,
    log_case_start,
    log_agent_action,
    log_policy_result,
    log_case_error,
    log_case_end,
    write_trace,
    calculate_policy_confidence,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Coordinator")


def process_case(case_id: str) -> bool:
    """Xử lý một case hoàn chỉnh."""
    logger.info(f"[{case_id}] Starting...")

    try:
        # Input
        case = read_input(case_id)
        claimed_order_id = get_case_order_id(case)
        log_case_start(case_id, claimed_order_id)

        if not claimed_order_id:
            raise ValueError("Missing claimed_order_id")

        logger.info(f"[{case_id}] Order: {claimed_order_id}")

        # Order & Seller Agent
        order_data = get_order_with_details(claimed_order_id)
        if "error" in order_data:
            raise ValueError(f"Order not found: {claimed_order_id}")

        order_status = order_data["order"].get("order_status", "")
        logger.info(f"[{case_id}] Status: {order_status}")

        # Delivery Agent
        delivery = analyze_delivery_timing(claimed_order_id)
        log_agent_action(case_id, "DeliveryAgent", "analyzed", {
            "late": delivery["is_late_delivery"],
            "late_sellers": delivery["late_sellers"],
            "on_time_sellers": delivery["on_time_sellers"],
            "margin_days": delivery.get("delivery_margin_days", 0),
        })

        # Payment Agent
        payment = check_payment_reconciliation(claimed_order_id)
        log_agent_action(case_id, "PaymentAgent", "checked", {
            "count": payment["payments_count"],
            "reconciled": payment["is_reconciled"],
        })

        # Policy Agent
        financials = order_data["financials"]
        
        policy_result = apply_policy(
            order_status=order_status,
            payment_total=financials["payment_total_brl"],
            is_late_delivery=delivery["is_late_delivery"],
            late_sellers=delivery["late_sellers"],
            on_time_sellers=delivery["on_time_sellers"],
            payments_count=payment["payments_count"],
            is_reconciled=payment["is_reconciled"],
            freight_total=financials["freight_total_brl"],
        )

        # Calculate confidence based on multi-agent evidence (not hardcoded)
        confidence = calculate_policy_confidence(
            primary_issue=policy_result.primary_issue,
            order_data=order_data,
            payment_data=payment,
            delivery_data=delivery,
        )

        logger.info(f"[{case_id}] Issue: {policy_result.primary_issue}, Refund: {policy_result.recommended_refund_brl} BRL, Confidence: {confidence:.2f}")
        log_policy_result(case_id, policy_result.primary_issue, confidence)

        # Build evidence IDs
        evidence_ids = [f"order:{claimed_order_id}"]

        for item in order_data["items"]:
            item_id = f"item:{claimed_order_id}:{item.get('order_item_id', 1)}"
            if item_id not in evidence_ids:
                evidence_ids.append(item_id)

        for payment_row in order_data["payments"]:
            payment_id = f"payment:{claimed_order_id}:{payment_row.get('payment_sequential', 1)}"
            if payment_id not in evidence_ids:
                evidence_ids.append(payment_id)

        for seller_id in order_data["seller_ids"]:
            seller_evidence = f"seller:{seller_id}"
            if seller_evidence not in evidence_ids:
                evidence_ids.append(seller_evidence)

        for cause in policy_result.root_cause_codes:
            policy_evidence = f"policy:{cause['cause_code']}"
            if policy_evidence not in evidence_ids:
                evidence_ids.append(policy_evidence)

        # Build output (using calculated confidence)
        output = build_output(
            case_id=case_id,
            primary_issue=policy_result.primary_issue,
            case_status=policy_result.case_status,
            confidence=confidence,
            order_ids=[claimed_order_id],
            item_ids=[f"{claimed_order_id}:{i.get('order_item_id', 1)}" for i in order_data["items"]],
            seller_ids=order_data["seller_ids"],
            payment_ids=[f"{claimed_order_id}:{p.get('payment_sequential', 1)}" for p in order_data["payments"]],
            ranked_causes=policy_result.root_cause_codes,
            responsible_parties=policy_result.responsible_parties,
            evidence_ids=evidence_ids,
            item_total_brl=financials["item_total_brl"],
            freight_total_brl=financials["freight_total_brl"],
            payment_total_brl=financials["payment_total_brl"],
            recommended_refund_brl=policy_result.recommended_refund_brl,
            resolution_actions=policy_result.resolution_actions,
        )

        # Validate
        is_valid, errors = validate_output_schema(output)
        if not is_valid:
            logger.warning(f"[{case_id}] Validation errors: {errors}")

        # Write
        write_output(case_id, output)
        log_case_end(case_id, "success")
        logger.info(f"[{case_id}] ✓ Done")
        return True

    except Exception as e:
        logger.error(f"[{case_id}] ✗ Error: {e}")
        log_case_error(case_id, e)
        log_case_end(case_id, "failed")
        return False


def main():
    parser = argparse.ArgumentParser(description="Coordinator Agent")
    parser.add_argument("--case", type=str, help="Process single case")
    parser.add_argument("--list", action="store_true", help="List cases")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("E-commerce Dispute Resolution - Coordinator Agent")
    logger.info("=" * 60)

    # Load data
    logger.info("Loading data...")
    load_all_csvs()
    logger.info("Data loaded")

    if args.list:
        cases = list_input_cases()
        print(f"\n{len(cases)} cases found:")
        for c in cases:
            print(f"  {c}")
        return

    if args.case:
        success = process_case(args.case)
        write_trace()
        sys.exit(0 if success else 1)

    # Process all
    cases = list_input_cases()
    logger.info(f"\nProcessing {len(cases)} cases...")

    results = {c: process_case(c) for c in cases}

    write_trace()

    success = sum(1 for v in results.values() if v)
    failed = len(results) - success

    print("\n" + "=" * 60)
    print(f"COMPLETE: {success}/{len(cases)} succeeded, {failed} failed")
    if failed > 0:
        print("Failed:", [c for c, s in results.items() if not s])
    print("=" * 60)


if __name__ == "__main__":
    main()
