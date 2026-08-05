"""
Detailed analysis of output files vs actual data.
Compare each output with the source data to find discrepancies.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"


def load_data():
    """Load all CSV files."""
    return {
        "orders": pd.read_csv(DATA_DIR / "olist_orders_dataset.csv"),
        "order_items": pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv"),
        "order_payments": pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv"),
        "sellers": pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv"),
    }


def analyze_case(case_id: str, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Analyze a single case against source data."""
    # Load input
    input_file = INPUT_DIR / f"{case_id}.json"
    if not input_file.exists():
        return {"error": f"Input file not found: {case_id}"}
    
    with open(input_file, "r", encoding="utf-8") as f:
        case_input = json.load(f)
    
    # Load output
    output_file = OUTPUT_DIR / f"{case_id}.json"
    if not output_file.exists():
        return {"error": f"Output file not found: {case_id}"}
    
    with open(output_file, "r", encoding="utf-8") as f:
        case_output = json.load(f)
    
    order_id = case_input.get("customer_request", {}).get("claimed_order_id")
    if not order_id:
        return {"error": "No claimed_order_id in input"}
    
    # Get source data
    orders = data["orders"]
    order_items = data["order_items"]
    order_payments = data["order_payments"]
    sellers = data["sellers"]
    
    # Filter to this order
    order_row = orders[orders["order_id"] == order_id]
    items = order_items[order_items["order_id"] == order_id]
    payments = order_payments[order_payments["order_id"] == order_id]
    
    if order_row.empty:
        return {"error": f"Order not found: {order_id}"}
    
    order = order_row.iloc[0]
    
    # Calculate actual values
    order_status = str(order.get("order_status", "")).strip().lower()
    
    # Calculate financials
    item_total = items["price"].sum() if not items.empty else 0.0
    freight_total = items["freight_value"].sum() if not items.empty else 0.0
    payment_total = payments["payment_value"].sum() if not payments.empty else 0.0
    
    # Check delivery timing
    order_delivered_carrier = pd.to_datetime(order.get("order_delivered_carrier_date"), errors="coerce")
    order_delivered_customer = pd.to_datetime(order.get("order_delivered_customer_date"), errors="coerce")
    order_estimated = pd.to_datetime(order.get("order_estimated_delivery_date"), errors="coerce")
    
    is_late_delivery = False
    if pd.notna(order_delivered_customer) and pd.notna(order_estimated):
        is_late_delivery = order_delivered_customer > order_estimated
    
    # Check seller late
    late_sellers = []
    on_time_sellers = []
    
    for _, item in items.iterrows():
        seller_id = item.get("seller_id")
        shipping_limit = pd.to_datetime(item.get("shipping_limit_date"), errors="coerce")
        
        if pd.notna(shipping_limit) and pd.notna(order_delivered_carrier):
            if order_delivered_carrier > shipping_limit:
                late_sellers.append(seller_id)
            else:
                on_time_sellers.append(seller_id)
    
    # Determine expected primary issue
    expected_issue = None
    expected_refund = 0.0
    expected_responsible = []
    expected_cause = None
    
    if order_status == "canceled" and payment_total > 0:
        expected_issue = "canceled_order_paid"
        expected_refund = round(payment_total, 2)
        expected_responsible = [("platform", "OLIST_PLATFORM")]
        expected_cause = "ORDER_CANCELED_AFTER_PAYMENT"
    elif order_status == "unavailable" and payment_total > 0:
        expected_issue = "unavailable_order_paid"
        expected_refund = round(payment_total, 2)
        expected_responsible = [("platform", "OLIST_PLATFORM")]
        expected_cause = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
    elif is_late_delivery and late_sellers:
        expected_issue = "late_delivery_seller"
        expected_refund = round(freight_total, 2)
        expected_responsible = [("seller", s) for s in set(late_sellers)]
        expected_cause = "SELLER_HANDOFF_AFTER_LIMIT"
    elif is_late_delivery and not late_sellers and on_time_sellers:
        expected_issue = "late_delivery_logistics"
        expected_refund = round(freight_total, 2)
        expected_responsible = [("logistics_provider", "LOGISTICS_PROVIDER")]
        expected_cause = "CARRIER_DELIVERED_AFTER_ESTIMATE"
    elif len(payments) >= 2 and abs(payment_total - (item_total + freight_total)) <= 0.10:
        expected_issue = "valid_split_payment"
        expected_refund = 0.0
        expected_responsible = []
        expected_cause = "MULTIPLE_PAYMENTS_RECONCILED"
    elif not is_late_delivery and abs(payment_total - (item_total + freight_total)) <= 0.10:
        expected_issue = "unsupported_late_claim"
        expected_refund = 0.0
        expected_responsible = []
        expected_cause = "DELIVERY_WITHIN_ESTIMATE"
    
    # Compare with output
    output_issue = case_output.get("assessment", {}).get("primary_issue")
    output_refund = case_output.get("financial_resolution", {}).get("recommended_refund_brl", 0)
    output_responsible = case_output.get("root_cause_analysis", {}).get("responsible_parties", [])
    output_cause = case_output.get("root_cause_analysis", {}).get("ranked_causes", [{}])[0].get("cause_code")
    
    # Compare financials
    output_item_total = case_output.get("financial_resolution", {}).get("item_total_brl", 0)
    output_freight_total = case_output.get("financial_resolution", {}).get("freight_total_brl", 0)
    output_payment_total = case_output.get("financial_resolution", {}).get("payment_total_brl", 0)
    
    # Build comparison result
    result = {
        "case_id": case_id,
        "order_id": order_id,
        "order_status": order_status,
        "is_late_delivery": is_late_delivery,
        "late_sellers": list(set(late_sellers)),
        "on_time_sellers": list(set(on_time_sellers)),
        
        "expected": {
            "primary_issue": expected_issue,
            "refund": expected_refund,
            "responsible": expected_responsible,
            "cause": expected_cause,
            "item_total": round(item_total, 2),
            "freight_total": round(freight_total, 2),
            "payment_total": round(payment_total, 2),
        },
        
        "output": {
            "primary_issue": output_issue,
            "refund": output_refund,
            "responsible": output_responsible,
            "cause": output_cause,
            "item_total": output_item_total,
            "freight_total": output_freight_total,
            "payment_total": output_payment_total,
        },
        
        "discrepancies": [],
        "score_potential": 0,
    }
    
    # Check discrepancies
    if expected_issue != output_issue:
        result["discrepancies"].append(f"Primary issue: expected '{expected_issue}', got '{output_issue}'")
    
    if abs(expected_refund - output_refund) > 0.01:
        result["discrepancies"].append(f"Refund: expected {expected_refund}, got {output_refund}")
    
    if round(item_total, 2) != output_item_total:
        result["discrepancies"].append(f"Item total: expected {round(item_total, 2)}, got {output_item_total}")
    
    if round(freight_total, 2) != output_freight_total:
        result["discrepancies"].append(f"Freight total: expected {round(freight_total, 2)}, got {output_freight_total}")
    
    if round(payment_total, 2) != output_payment_total:
        result["discrepancies"].append(f"Payment total: expected {round(payment_total, 2)}, got {output_payment_total}")
    
    if expected_cause != output_cause:
        result["discrepancies"].append(f"Cause: expected '{expected_cause}', got '{output_cause}'")
    
    # Calculate score potential (rough estimate)
    if not result["discrepancies"]:
        result["score_potential"] = 100
    else:
        # Rough estimate based on discrepancies
        score_loss_per_issue = 15  # ~60% max loss if all 4 components affected
        result["score_potential"] = max(0, 100 - len(result["discrepancies"]) * score_loss_per_issue)
    
    return result


def main():
    """Analyze all cases."""
    print("Loading data...")
    data = load_data()
    
    case_ids = [f"EC_{i:03d}" for i in range(1, 51)]
    results = []
    
    for case_id in case_ids:
        result = analyze_case(case_id, data)
        if "error" not in result:
            results.append(result)
    
    # Sort by discrepancies
    results.sort(key=lambda x: -len(x["discrepancies"]))
    
    # Print summary
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS RESULTS")
    print("=" * 80)
    
    total_discrepancies = sum(len(r["discrepancies"]) for r in results)
    cases_with_issues = sum(1 for r in results if r["discrepancies"])
    
    print(f"\nTotal cases: {len(results)}")
    print(f"Cases with issues: {cases_with_issues}")
    print(f"Total discrepancies: {total_discrepancies}")
    print(f"Avg score potential: {sum(r['score_potential'] for r in results) / len(results):.1f}%")
    
    # Print cases with issues
    print("\n" + "-" * 80)
    print("CASES WITH DISCREPANCIES:")
    print("-" * 80)
    
    for r in results:
        if r["discrepancies"]:
            print(f"\n{r['case_id']} - {r['order_status']} - late={r['is_late_delivery']}")
            print(f"  Expected: {r['expected']['primary_issue']} | Output: {r['output']['primary_issue']}")
            for d in r["discrepancies"]:
                print(f"    - {d}")
    
    # Group discrepancies by type
    print("\n" + "-" * 80)
    print("DISCREPANCY BREAKDOWN:")
    print("-" * 80)
    
    discrepancy_types = {}
    for r in results:
        for d in r["discrepancies"]:
            key = d.split(":")[0].strip()
            discrepancy_types[key] = discrepancy_types.get(key, 0) + 1
    
    for dtype, count in sorted(discrepancy_types.items(), key=lambda x: -x[1]):
        print(f"  {dtype}: {count}")
    
    # Primary issue distribution
    print("\n" + "-" * 80)
    print("EXPECTED PRIMARY ISSUE DISTRIBUTION:")
    print("-" * 80)
    
    issue_counts = {}
    for r in results:
        issue = r["expected"]["primary_issue"]
        issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        print(f"  {issue}: {count}")
    
    # Output primary issue distribution
    print("\n" + "-" * 80)
    print("OUTPUT PRIMARY ISSUE DISTRIBUTION:")
    print("-" * 80)
    
    output_issue_counts = {}
    for r in results:
        issue = r["output"]["primary_issue"]
        output_issue_counts[issue] = output_issue_counts.get(issue, 0) + 1
    
    for issue, count in sorted(output_issue_counts.items(), key=lambda x: -x[1]):
        print(f"  {issue}: {count}")


if __name__ == "__main__":
    main()
