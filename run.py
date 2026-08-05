"""
Main Entry Point
Chạy xử lý tất cả 50 cases.

Usage:
    python run.py
    python run.py --case EC_001
    python run.py --list-cases
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

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
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_case(case_id: str) -> bool:
    """
    Xử lý một case.

    Args:
        case_id: Case ID (e.g., "EC_001")

    Returns:
        True nếu thành công, False otherwise
    """
    logger.info(f"Processing {case_id}")

    try:
        # Log start
        case = read_input(case_id)
        claimed_order_id = get_case_order_id(case)
        log_case_start(case_id, claimed_order_id)

        if not claimed_order_id:
            logger.error(f"No claimed_order_id in {case_id}")
            log_case_error(case_id, ValueError("Missing claimed_order_id"))
            log_case_end(case_id, "failed")
            return False

        log_agent_action(case_id, "Coordinator", "received_case", {"order_id": claimed_order_id})

        # Get order details
        order_data = get_order_with_details(claimed_order_id)
        if "error" in order_data:
            logger.error(f"Order not found: {claimed_order_id}")
            log_case_error(case_id, ValueError(f"Order not found: {claimed_order_id}"))
            log_case_end(case_id, "failed")
            return False

        log_agent_action(case_id, "OrderAgent", "fetched_order_details", {"status": order_data["order"].get("order_status")})

        # Analyze delivery timing
        delivery_data = analyze_delivery_timing(claimed_order_id)
        log_agent_action(case_id, "DeliveryAgent", "analyzed_timing", {
            "is_late": delivery_data["is_late_delivery"],
            "late_sellers": delivery_data["late_sellers"],
            "on_time_sellers": delivery_data["on_time_sellers"],
        })

        # Check payment reconciliation
        payment_data = check_payment_reconciliation(claimed_order_id)
        log_agent_action(case_id, "PaymentAgent", "checked_reconciliation", {
            "payments_count": payment_data["payments_count"],
            "is_reconciled": payment_data["is_reconciled"],
        })

        # Extract data for policy
        order = order_data["order"]
        financials = order_data["financials"]
        items = order_data["items"]
        payments = order_data["payments"]

        # Apply policy
        policy_result = apply_policy(
            order_status=order.get("order_status", ""),
            payment_total=financials["payment_total_brl"],
            is_late_delivery=delivery_data["is_late_delivery"],
            late_sellers=delivery_data["late_sellers"],
            on_time_sellers=delivery_data["on_time_sellers"],
            payments_count=payment_data["payments_count"],
            is_reconciled=payment_data["is_reconciled"],
            freight_total=financials["freight_total_brl"],
        )

        log_policy_result(case_id, policy_result.primary_issue, policy_result.confidence)
        log_agent_action(case_id, "PolicyAgent", "applied_policy", {
            "primary_issue": policy_result.primary_issue,
            "refund": policy_result.recommended_refund_brl,
        })

        # Build evidence IDs
        evidence_ids = [f"order:{claimed_order_id}"]

        # Add item evidence
        for item in items:
            item_id = f"item:{claimed_order_id}:{item.get('order_item_id', 1)}"
            if item_id not in evidence_ids:
                evidence_ids.append(item_id)

        # Add payment evidence
        for payment in payments:
            payment_id = f"payment:{claimed_order_id}:{payment.get('payment_sequential', 1)}"
            if payment_id not in evidence_ids:
                evidence_ids.append(payment_id)

        # Add seller evidence
        for seller_id in order_data["seller_ids"]:
            seller_evidence = f"seller:{seller_id}"
            if seller_evidence not in evidence_ids:
                evidence_ids.append(seller_evidence)

        # Add policy evidence
        for cause in policy_result.root_cause_codes:
            policy_evidence = f"policy:{cause['cause_code']}"
            if policy_evidence not in evidence_ids:
                evidence_ids.append(policy_evidence)

        # Build item IDs and seller IDs for affected_entities
        item_ids = [f"{claimed_order_id}:{item.get('order_item_id', 1)}" for item in items]
        seller_ids = order_data["seller_ids"]
        payment_ids = [f"{claimed_order_id}:{p.get('payment_sequential', 1)}" for p in payments]

        # Build output
        output = build_output(
            case_id=case_id,
            primary_issue=policy_result.primary_issue,
            case_status=policy_result.case_status,
            confidence=policy_result.confidence,
            order_ids=[claimed_order_id],
            item_ids=item_ids,
            seller_ids=seller_ids,
            payment_ids=payment_ids,
            ranked_causes=policy_result.root_cause_codes,
            responsible_parties=policy_result.responsible_parties,
            evidence_ids=evidence_ids,
            item_total_brl=financials["item_total_brl"],
            freight_total_brl=financials["freight_total_brl"],
            payment_total_brl=financials["payment_total_brl"],
            recommended_refund_brl=policy_result.recommended_refund_brl,
            resolution_actions=policy_result.resolution_actions,
        )

        # Validate output
        is_valid, errors = validate_output_schema(output)
        if not is_valid:
            logger.warning(f"Validation errors for {case_id}: {errors}")
            log_agent_action(case_id, "VerifierAgent", "validation_errors", {"errors": errors})

        # Write output
        write_output(case_id, output)
        log_agent_action(case_id, "OutputWriter", "wrote_file", {"path": f"output/{case_id}.json"})

        log_case_end(case_id, "success")
        logger.info(f"✓ {case_id} completed successfully")
        return True

    except Exception as e:
        logger.error(f"✗ {case_id} failed: {e}")
        log_case_error(case_id, e)
        log_case_end(case_id, "failed")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process e-commerce dispute cases")
    parser.add_argument("--case", type=str, help="Process specific case (e.g., EC_001)")
    parser.add_argument("--list-cases", action="store_true", help="List all input cases")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Preload data
    logger.info("Loading CSV data...")
    load_all_csvs()
    logger.info("Data loaded successfully")

    if args.list_cases:
        cases = list_input_cases()
        print(f"Found {len(cases)} input cases:")
        for case_id in cases:
            print(f"  - {case_id}")
        return

    if args.case:
        # Process single case
        success = process_case(args.case)
        write_trace()
        sys.exit(0 if success else 1)

    # Process all cases
    cases = list_input_cases()
    logger.info(f"Processing {len(cases)} cases...")

    results = {}
    for case_id in cases:
        results[case_id] = process_case(case_id)

    # Write trace
    write_trace()

    # Summary
    success_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - success_count

    logger.info("=" * 50)
    logger.info(f"Processing complete!")
    logger.info(f"  Success: {success_count}/{len(cases)}")
    logger.info(f"  Failed: {failed_count}/{len(cases)}")

    if failed_count > 0:
        logger.info("Failed cases:")
        for case_id, success in results.items():
            if not success:
                logger.info(f"  - {case_id}")

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
