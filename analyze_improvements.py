"""
Analyze outputs for potential improvements
"""
import json
import pandas as pd
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")

def load_data():
    orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
    items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")
    sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv")
    return orders, items, payments, sellers

def analyze_output(case_id, orders, items, payments, sellers):
    """Phân tích một output file"""
    with open(OUTPUT_DIR / f"{case_id}.json") as f:
        output = json.load(f)
    
    claimed_order_id = None
    with open(f"input/{case_id}.json") as f:
        case = json.load(f)
        claimed_order_id = case["customer_request"]["claimed_order_id"]
    
    issues = []
    
    # Get actual data
    order = orders[orders["order_id"] == claimed_order_id]
    if not order.empty:
        order_status = str(order.iloc[0]["order_status"]).lower()
        actual_items = items[items["order_id"] == claimed_order_id]
        actual_payments = payments[payments["order_id"] == claimed_order_id]
        
        # Check item_ids format
        for item_id in output["affected_entities"]["item_ids"]:
            parts = item_id.split(":")
            if len(parts) == 3:
                order_id_from_item = parts[1]
                item_seq = int(parts[2])
                # Verify this item exists
                if item_seq not in actual_items["order_item_id"].values:
                    issues.append(f"ITEM_NOT_FOUND: {item_id}")
            else:
                issues.append(f"ITEM_FORMAT_INVALID: {item_id}")
        
        # Check payment_ids format
        for pay_id in output["affected_entities"]["payment_ids"]:
            parts = pay_id.split(":")
            if len(parts) == 3:
                order_id_from_pay = parts[1]
                pay_seq = int(parts[2])
                # Verify this payment exists
                if pay_seq not in actual_payments["payment_sequential"].values:
                    issues.append(f"PAYMENT_NOT_FOUND: {pay_id}")
            else:
                issues.append(f"PAYMENT_FORMAT_INVALID: {pay_id}")
    
    # Check financial consistency
    fin = output["financial_resolution"]
    item_total = fin["item_total_brl"]
    freight_total = fin["freight_total_brl"]
    payment_total = fin["payment_total_brl"]
    refund = fin["recommended_refund_brl"]
    
    primary_issue = output["assessment"]["primary_issue"]
    
    # Validate based on issue type
    if primary_issue in ["canceled_order_paid", "unavailable_order_paid"]:
        if abs(refund - payment_total) > 0.01:
            issues.append(f"REFUND_MISMATCH: expected={payment_total}, got={refund}")
    elif primary_issue in ["late_delivery_seller", "late_delivery_logistics"]:
        if abs(refund - freight_total) > 0.01:
            issues.append(f"REFUND_MISMATCH: expected={freight_total}, got={refund}")
    elif primary_issue in ["valid_split_payment", "unsupported_late_claim"]:
        if refund != 0.0:
            issues.append(f"REFUND_SHOULD_BE_ZERO: got={refund}")
    
    return issues

def main():
    orders, items, payments, sellers = load_data()
    
    all_issues = []
    issue_counter = Counter()
    
    for i in range(1, 51):
        case_id = f"EC_{i:03d}"
        issues = analyze_output(case_id, orders, items, payments, sellers)
        if issues:
            for issue in issues:
                issue_counter[issue] += 1
                all_issues.append((case_id, issue))
    
    print("=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    
    if all_issues:
        print(f"\nFound {len(all_issues)} issues in {len(set(c[0] for c in all_issues))} cases:")
        print()
        for issue_type, count in issue_counter.most_common():
            print(f"  {issue_type}: {count}")
        
        print("\nDetailed issues:")
        for case_id, issue in all_issues[:20]:  # Show first 20
            print(f"  {case_id}: {issue}")
    else:
        print("\nNo issues found! All outputs look correct.")
    
    # Check payment_sequential distribution
    print("\n" + "=" * 60)
    print("PAYMENT SEQUENTIAL DISTRIBUTION")
    print("=" * 60)
    print(payments["payment_sequential"].value_counts().head(10))
    
    # Check order_item_id distribution
    print("\n" + "=" * 60)
    print("ORDER_ITEM_ID DISTRIBUTION")
    print("=" * 60)
    print(items["order_item_id"].value_counts().head(10))

if __name__ == "__main__":
    main()
