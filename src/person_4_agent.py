"""
Person 4 Agent - Payment & Delivery Analysis
Cases: EC_031 - EC_040

Reuses the shared data_loader helpers (check_payment_reconciliation,
analyze_delivery_timing) that Person 1 built, so the split/reconciliation
and delivery-lateness logic stays identical to what Person 5 uses on their
case range and what Person 6 will re-check when applying EC_POLICY_V1.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import (
    load_all_csvs,
    read_input,
    get_case_order_id,
    get_order_with_details,
    check_payment_reconciliation,
    analyze_delivery_timing,
)

BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed" / "person_4"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CASES = [f"EC_0{i:02d}" for i in range(31, 41)]


def main():
    print("Starting Payment & Delivery Analysis for Person 4...")
    load_all_csvs()

    for case_id in CASES:
        print(f"Processing case: {case_id}")
        case = read_input(case_id)
        order_id = get_case_order_id(case)
        if not order_id:
            print(f"Warning: Case {case_id} has no order_id!")
            continue

        details = get_order_with_details(order_id)
        if "error" in details:
            print(f"Error: Order {order_id} not found in database.")
            continue

        payment_check = check_payment_reconciliation(order_id)
        delivery = analyze_delivery_timing(order_id)

        payment_rows = []
        payment_evidence_ids = []
        for p in details["payments"]:
            seq = p.get("payment_sequential", 1)
            payment_rows.append(
                {
                    "payment_sequential": seq,
                    "payment_type": p.get("payment_type"),
                    "payment_installments": p.get("payment_installments"),
                    "payment_value": round(float(p.get("payment_value", 0.0)), 2),
                }
            )
            payment_evidence_ids.append(f"payment:{order_id}:{seq}")

        result = {
            "case_id": case_id,
            "order_id": order_id,
            "order_status": details["order"].get("order_status"),
            "order_estimated_delivery_date": delivery.get("estimated_delivery"),
            "order_delivered_customer_date": delivery.get("delivered_customer"),
            "is_late_delivery": delivery.get("is_late_delivery"),
            "late_sellers": delivery.get("late_sellers"),
            "on_time_sellers": delivery.get("on_time_sellers"),
            "payments": payment_rows,
            "payments_count": payment_check["payments_count"],
            "is_split_payment": payment_check["is_split_payment"],
            "item_total_brl": payment_check["item_total_brl"],
            "freight_total_brl": payment_check["freight_total_brl"],
            "expected_total_brl": payment_check["expected_total_brl"],
            "payment_total_brl": payment_check["payment_total_brl"],
            "difference_brl": payment_check["difference_brl"],
            "is_reconciled": payment_check["is_reconciled"],
            "evidence_ids": [f"order:{order_id}"] + payment_evidence_ids,
        }

        out_path = PROCESSED_DIR / f"{case_id}_processed.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Saved {case_id} intermediate results to {out_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
