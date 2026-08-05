"""
Deep analysis for scoring improvements
"""
import json
import pandas as pd
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
INPUT_DIR = Path("input")

def load_data():
    orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
    items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")
    sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv")
    return orders, items, payments, sellers

def get_ground_truth(order_id, orders, items, payments):
    """Tính ground truth cho một order"""
    order = orders[orders["order_id"] == order_id]
    if order.empty:
        return None
    
    order_status = str(order.iloc[0]["order_status"]).strip().lower()
    order_items = items[items["order_id"] == order_id]
    order_payments = payments[payments["order_id"] == order_id]
    
    # Check if canceled or unavailable
    if order_status == "canceled" and order_payments["payment_value"].sum() > 0:
        return {
            "issue": "canceled_order_paid",
            "refund": round(order_payments["payment_value"].sum(), 2),
            "status": "action_required"
        }
    
    if order_status == "unavailable" and order_payments["payment_value"].sum() > 0:
        return {
            "issue": "unavailable_order_paid",
            "refund": round(order_payments["payment_value"].sum(), 2),
            "status": "action_required"
        }
    
    # For delivery analysis
    freight_total = order_items["freight_value"].sum()
    
    # Check late delivery
    delivered = pd.to_datetime(order.iloc[0].get("order_delivered_customer_date"), errors="coerce")
    estimated = pd.to_datetime(order.iloc[0].get("order_estimated_delivery_date"), errors="coerce")
    carrier_date = pd.to_datetime(order.iloc[0].get("order_delivered_carrier_date"), errors="coerce")
    
    if pd.notna(delivered) and pd.notna(estimated) and delivered > estimated:
        # Late delivery - check seller responsibility
        late_sellers = []
        on_time_sellers = []
        
        for _, item in order_items.iterrows():
            seller_id = item["seller_id"]
            shipping_limit = pd.to_datetime(item["shipping_limit_date"], errors="coerce")
            
            if pd.notna(shipping_limit) and pd.notna(carrier_date):
                if carrier_date > shipping_limit:
                    late_sellers.append(seller_id)
                else:
                    on_time_sellers.append(seller_id)
        
        if late_sellers:
            return {
                "issue": "late_delivery_seller",
                "refund": round(freight_total, 2),
                "status": "action_required"
            }
        elif on_time_sellers:
            return {
                "issue": "late_delivery_logistics",
                "refund": round(freight_total, 2),
                "status": "action_required"
            }
    
    # Check split payment
    if len(order_payments) >= 2:
        item_total = order_items["price"].sum()
        expected = round(item_total + freight_total, 2)
        actual = round(order_payments["payment_value"].sum(), 2)
        diff = abs(actual - expected)
        
        if diff <= 0.10:
            return {
                "issue": "valid_split_payment",
                "refund": 0.0,
                "status": "no_action"
            }
    
    # Default to unsupported claim if delivered on time
    if pd.notna(delivered) and pd.notna(estimated) and delivered <= estimated:
        return {
            "issue": "unsupported_late_claim",
            "refund": 0.0,
            "status": "no_action"
        }
    
    return None

def analyze_case(case_id, orders, items, payments, sellers):
    """Analyze one case and return scoring details"""
    with open(OUTPUT_DIR / f"{case_id}.json") as f:
        output = json.load(f)
    
    with open(INPUT_DIR / f"{case_id}.json") as f:
        case = json.load(f)
    
    order_id = case["customer_request"]["claimed_order_id"]
    ground_truth = get_ground_truth(order_id, orders, items, payments)
    
    if not ground_truth:
        return {"case_id": case_id, "error": "Could not compute ground truth"}
    
    output_issue = output["assessment"]["primary_issue"]
    output_refund = output["financial_resolution"]["recommended_refund_brl"]
    output_status = output["assessment"]["case_status"]
    
    # Calculate scores
    scores = {}
    
    # 1. Primary issue match (20%)
    if output_issue == ground_truth["issue"]:
        scores["issue"] = 1.0
    else:
        scores["issue"] = 0.0
        print(f"  ISSUE MISMATCH: {case_id} - GT={ground_truth['issue']}, Output={output_issue}")
    
    # 2. Affected entities (20%)
    # This is harder to score without ground truth for entities
    scores["entities"] = 1.0  # Assuming correct since we verified format
    
    # 3. Root cause (15%)
    output_causes = [c["cause_code"] for c in output["root_cause_analysis"]["ranked_causes"]]
    expected_causes = {
        "canceled_order_paid": "ORDER_CANCELED_AFTER_PAYMENT",
        "unavailable_order_paid": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
        "late_delivery_seller": "SELLER_HANDOFF_AFTER_LIMIT",
        "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
        "valid_split_payment": "MULTIPLE_PAYMENTS_RECONCILED",
        "unsupported_late_claim": "DELIVERY_WITHIN_ESTIMATE",
    }
    expected_cause = expected_causes.get(ground_truth["issue"])
    if expected_cause in output_causes:
        scores["root_cause"] = 1.0
    else:
        scores["root_cause"] = 0.5
        print(f"  ROOT CAUSE MISMATCH: {case_id} - Expected={expected_cause}, Got={output_causes}")
    
    # 4. Financial resolution (20%)
    gt_refund = ground_truth["refund"]
    if abs(output_refund - gt_refund) < 0.01:
        scores["financial"] = 1.0
    elif abs(output_refund - gt_refund) < 1.0:
        scores["financial"] = 0.8
    else:
        scores["financial"] = 0.0
        print(f"  FINANCIAL MISMATCH: {case_id} - GT={gt_refund}, Output={output_refund}")
    
    # 5. Resolution actions (10%)
    output_actions = output["resolution_actions"]
    expected_actions = {
        "canceled_order_paid": ["issue_full_refund"],
        "unavailable_order_paid": ["issue_full_refund"],
        "late_delivery_seller": ["refund_freight"],
        "late_delivery_logistics": ["refund_freight"],
        "valid_split_payment": ["explain_valid_split_payment"],
        "unsupported_late_claim": ["reject_late_refund"],
    }
    gt_actions = expected_actions.get(ground_truth["issue"], [])
    if set(gt_actions) == set(output_actions):
        scores["actions"] = 1.0
    else:
        scores["actions"] = 0.5
        print(f"  ACTIONS MISMATCH: {case_id} - Expected={gt_actions}, Got={output_actions}")
    
    # 6. Confidence (part of issue scoring)
    # Lower confidence might hurt if ground truth is 100% certain
    output_conf = output["assessment"]["confidence"]
    if ground_truth["issue"] in ["canceled_order_paid", "unavailable_order_paid"]:
        # These are deterministic - should be 1.0
        if output_conf < 1.0:
            print(f"  LOW CONFIDENCE: {case_id} - {output_conf}")
    
    return {
        "case_id": case_id,
        "ground_truth": ground_truth,
        "output": {
            "issue": output_issue,
            "refund": output_refund,
            "status": output_status,
            "confidence": output["assessment"]["confidence"]
        },
        "scores": scores,
        "total_score": (
            scores["issue"] * 0.20 +
            scores["entities"] * 0.20 +
            scores["root_cause"] * 0.15 +
            scores["financial"] * 0.20 +
            scores["actions"] * 0.10
        ) * 100
    }

def main():
    orders, items, payments, sellers = load_data()
    
    results = []
    for i in range(1, 51):
        case_id = f"EC_{i:03d}"
        result = analyze_case(case_id, orders, items, payments, sellers)
        results.append(result)
    
    # Calculate overall score
    total_score = sum(r["total_score"] for r in results) / len(results)
    
    print("\n" + "=" * 60)
    print("SCORING SUMMARY")
    print("=" * 60)
    print(f"\nEstimated Score: {total_score:.2f}%")
    
    # Breakdown
    score_types = ["issue", "entities", "root_cause", "financial", "actions"]
    for stype in score_types:
        avg = sum(r["scores"][stype] for r in results) / len(results) * 100
        print(f"  {stype}: {avg:.2f}%")
    
    # Issues found
    print("\n" + "=" * 60)
    print("DETAILED ISSUES")
    print("=" * 60)
    
    perfect = [r for r in results if r["total_score"] == 100]
    partial = [r for r in results if 0 < r["total_score"] < 100]
    failed = [r for r in results if "error" in r or r["total_score"] == 0]
    
    print(f"Perfect (100%): {len(perfect)}")
    print(f"Partial (0-100%): {len(partial)}")
    print(f"Failed (0%): {len(failed)}")
    
    if partial:
        print("\nPartial cases:")
        for r in partial:
            print(f"  {r['case_id']}: {r['total_score']:.1f}% - GT={r['ground_truth']['issue']}, Out={r['output']['issue']}")

if __name__ == "__main__":
    main()
