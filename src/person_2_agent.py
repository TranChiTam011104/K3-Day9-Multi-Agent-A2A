import os
import json
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path to allow importing from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import (
    load_all_csvs,
    get_order_with_details,
    read_input,
    get_case_order_id
)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed" / "person_2"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CASES = [
    f"EC_0{i:02d}" for i in range(1, 11)
] + [
    f"EC_0{i:02d}" for i in range(21, 26)
]

def main():
    print(f"Starting Order & Seller Processing for Person 2...")
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
            
        order = details["order"]
        items = details["items"]
        
        order_status = order.get("order_status", "")
        delivered_carrier = order.get("order_delivered_carrier_date")
        
        processed_items = []
        freight_total_brl = 0.0
        violating_sellers = []
        
        for item in items:
            item_seq = item.get("order_item_id", 1)
            item_id = f"item:{order_id}:{item_seq}"
            seller_id = item.get("seller_id", "")
            limit_date = item.get("shipping_limit_date")
            freight_value = float(item.get("freight_value", 0.0))
            freight_total_brl += freight_value
            
            # Check late handoff
            is_late_handoff = False
            if pd.notna(limit_date) and pd.notna(delivered_carrier):
                if delivered_carrier > limit_date:
                    is_late_handoff = True
                    if seller_id not in violating_sellers:
                        violating_sellers.append(seller_id)
            
            processed_items.append({
                "item_id": item_id,
                "seller_id": seller_id,
                "shipping_limit_date": str(limit_date) if pd.notna(limit_date) else None,
                "freight_value": freight_value,
                "is_late_handoff": is_late_handoff
            })
            
        seller_ids = list(set([item.get("seller_id") for item in items if item.get("seller_id")]))
        
        # Build output structure for Person 2
        result = {
            "case_id": case_id,
            "order_id": order_id,
            "order_status": order_status,
            "order_delivered_carrier_date": str(delivered_carrier) if pd.notna(delivered_carrier) else None,
            "freight_total_brl": round(freight_total_brl, 2),
            "seller_ids": seller_ids,
            "violating_sellers": violating_sellers,
            "items": processed_items,
            "evidence_ids": [
                f"order:{order_id}"
            ] + [
                f"item:{order_id}:{item.get('order_item_id', 1)}" for item in items
            ] + [
                f"seller:{sid}" for sid in seller_ids
            ]
        }
        
        out_path = PROCESSED_DIR / f"{case_id}_processed.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        print(f"Saved {case_id} intermediate results to {out_path.relative_to(BASE_DIR)}")

if __name__ == "__main__":
    main()
