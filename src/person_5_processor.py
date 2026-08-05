"""Payment and delivery handoff producer for Person 5 (EC_041--EC_050).

This module deliberately stops at verified intermediate facts. Applying
``EC_POLICY_V1`` and creating the final files in ``output/`` belong to the
coordinator (Person 6).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from .data_loader import get_order_with_details, load_csv
from .validators import validate_evidence_ids, verify_evidence_exists_in_csv


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = REPO_ROOT / "input"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "person_5"
PERSON_5_CASE_IDS = tuple(f"EC_{number:03d}" for number in range(41, 51))
PAYMENT_TOLERANCE_BRL = 0.10


def _optional_text(value: Any) -> Optional[str]:
    """Return a JSON-safe string, preserving a missing CSV value as null."""
    if value is None or pd.isna(value):
        return None
    return str(value)


def _timestamp(value: Any) -> Optional[pd.Timestamp]:
    """Parse an Olist timestamp without inventing a timezone."""
    text = _optional_text(value)
    if text is None:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    return None if pd.isna(parsed) else parsed


def _is_after(left: Any, right: Any) -> Optional[bool]:
    """Compare timestamps; return null when either source value is missing."""
    left_timestamp = _timestamp(left)
    right_timestamp = _timestamp(right)
    if left_timestamp is None or right_timestamp is None:
        return None
    return bool(left_timestamp > right_timestamp)


def _read_case(case_id: str, input_dir: Path) -> Dict[str, Any]:
    if case_id not in PERSON_5_CASE_IDS:
        raise ValueError(f"{case_id} is outside Person 5 scope (EC_041--EC_050)")

    path = input_dir / f"{case_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Input case not found: {path}")

    with path.open("r", encoding="utf-8") as stream:
        case = json.load(stream)

    if case.get("case_id") != case_id:
        raise ValueError(f"Case ID mismatch in {path}")
    if case.get("policy_version") != "EC_POLICY_V1":
        raise ValueError(f"Unsupported policy version in {path}")
    if not case.get("customer_request", {}).get("claimed_order_id"):
        raise ValueError(f"Missing claimed_order_id in {path}")
    return case


def _verified_evidence_ids(order_id: str, items: List[Dict[str, Any]], payments: List[Dict[str, Any]]) -> List[str]:
    seller_ids = sorted({str(item["seller_id"]) for item in items})
    evidence_ids = [f"order:{order_id}"]
    evidence_ids.extend(
        f"item:{order_id}:{int(item['order_item_id'])}"
        for item in sorted(items, key=lambda row: int(row["order_item_id"]))
    )
    evidence_ids.extend(
        f"payment:{order_id}:{int(payment['payment_sequential'])}"
        for payment in sorted(payments, key=lambda row: int(row["payment_sequential"]))
    )
    evidence_ids.extend(f"seller:{seller_id}" for seller_id in seller_ids)

    format_valid, format_errors = validate_evidence_ids(evidence_ids)
    if not format_valid:
        raise ValueError(f"Invalid evidence IDs: {format_errors}")

    data_cache = {
        "olist_orders_dataset.csv": load_csv("olist_orders_dataset.csv"),
        "olist_order_items_dataset.csv": load_csv("olist_order_items_dataset.csv"),
        "olist_order_payments_dataset.csv": load_csv("olist_order_payments_dataset.csv"),
        "olist_sellers_dataset.csv": load_csv("olist_sellers_dataset.csv"),
    }
    missing = [
        evidence_id
        for evidence_id in evidence_ids
        if not verify_evidence_exists_in_csv(evidence_id, data_cache)[0]
    ]
    if missing:
        raise ValueError(f"Evidence IDs absent from source CSVs: {missing}")
    return evidence_ids


def analyze_person_5_case(case_id: str, input_dir: Path = DEFAULT_INPUT_DIR) -> Dict[str, Any]:
    """Build the verified payment/delivery handoff for one owned case."""
    case = _read_case(case_id, Path(input_dir))
    order_id = case["customer_request"]["claimed_order_id"]
    order_data = get_order_with_details(order_id)
    if "error" in order_data:
        raise ValueError(order_data["error"])

    order = order_data["order"]
    items = order_data["items"]
    payments = order_data["payments"]

    item_total = round(sum(float(item["price"]) for item in items), 2)
    freight_total = round(sum(float(item["freight_value"]) for item in items), 2)
    payment_total = round(sum(float(payment["payment_value"]) for payment in payments), 2)
    expected_total = round(item_total + freight_total, 2)
    difference = round(payment_total - expected_total, 2)

    delivered_customer = order.get("order_delivered_customer_date")
    estimated_delivery = order.get("order_estimated_delivery_date")
    delivered_carrier = order.get("order_delivered_carrier_date")

    payment_rows = [
        {
            "payment_sequential": int(payment["payment_sequential"]),
            "payment_type": str(payment["payment_type"]),
            "payment_installments": int(payment["payment_installments"]),
            "payment_value_brl": round(float(payment["payment_value"]), 2),
            "evidence_id": f"payment:{order_id}:{int(payment['payment_sequential'])}",
        }
        for payment in sorted(payments, key=lambda row: int(row["payment_sequential"]))
    ]

    seller_handoffs = [
        {
            "order_item_id": int(item["order_item_id"]),
            "seller_id": str(item["seller_id"]),
            "shipping_limit_date": _optional_text(item.get("shipping_limit_date")),
            "delivered_carrier_date": _optional_text(delivered_carrier),
            "handoff_after_shipping_limit": _is_after(
                delivered_carrier, item.get("shipping_limit_date")
            ),
            "item_evidence_id": f"item:{order_id}:{int(item['order_item_id'])}",
            "seller_evidence_id": f"seller:{item['seller_id']}",
        }
        for item in sorted(items, key=lambda row: int(row["order_item_id"]))
    ]

    evidence_ids = _verified_evidence_ids(order_id, items, payments)
    return {
        "case_id": case_id,
        "claimed_order_id": order_id,
        "policy_version": case["policy_version"],
        "producer": "person_5_payment_delivery",
        "source_tables": [
            "olist_orders_dataset.csv",
            "olist_order_items_dataset.csv",
            "olist_order_payments_dataset.csv",
            "olist_sellers_dataset.csv",
        ],
        "order_status": str(order["order_status"]),
        "payment_analysis": {
            "payments_count": len(payment_rows),
            "is_split_payment": len(payment_rows) >= 2,
            "payment_total_brl": payment_total,
            "payments": payment_rows,
        },
        "delivery_analysis": {
            "estimated_delivery_date": _optional_text(estimated_delivery),
            "delivered_customer_date": _optional_text(delivered_customer),
            "delivered_carrier_date": _optional_text(delivered_carrier),
            "delivered_after_estimate": _is_after(delivered_customer, estimated_delivery),
            "seller_handoffs": seller_handoffs,
        },
        "financial_analysis": {
            "item_total_brl": item_total,
            "freight_total_brl": freight_total,
            "expected_total_brl": expected_total,
            "payment_total_brl": payment_total,
            "difference_brl": difference,
            "tolerance_brl": PAYMENT_TOLERANCE_BRL,
            "is_reconciled": abs(difference) <= PAYMENT_TOLERANCE_BRL,
        },
        "evidence_ids": evidence_ids,
    }


def write_person_5_results(
    case_ids: Iterable[str] = PERSON_5_CASE_IDS,
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> List[Path]:
    """Write one deterministic JSON handoff per requested Person 5 case."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for case_id in case_ids:
        result = analyze_person_5_case(case_id, Path(input_dir))
        path = target_dir / f"{case_id}.json"
        with path.open("w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Produce Person 5 payment/delivery handoffs")
    parser.add_argument("--case", choices=PERSON_5_CASE_IDS, help="Process one owned case")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    case_ids = (args.case,) if args.case else PERSON_5_CASE_IDS
    written = write_person_5_results(case_ids=case_ids, output_dir=args.output_dir)
    print(f"Wrote {len(written)} Person 5 handoff file(s) to {args.output_dir}")


if __name__ == "__main__":
    main()
