"""
Verify all evidence IDs against CSV data.
Check if all evidence IDs exist in the original data.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import pandas as pd

# Use correct path
DATA_DIR = Path(__file__).parent / "data"


def load_all_evidence_ids() -> Dict[str, Set[str]]:
    """Load all IDs from CSV files into memory for fast lookup."""
    print("Loading CSV data for verification...")
    
    # Load CSV files
    orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
    order_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    order_payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")
    sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv")
    
    # Build lookup sets
    evidence_sets = {
        "order": set(orders["order_id"].dropna().astype(str).unique()),
        "item": set(),
        "payment": set(),
        "seller": set(sellers["seller_id"].dropna().astype(str).unique()),
    }
    
    # Build item IDs: order_id:order_item_id
    for _, row in order_items.iterrows():
        order_id = str(row.get("order_id")) if pd.notna(row.get("order_id")) else None
        order_item_id = row.get("order_item_id")
        if order_id and pd.notna(order_item_id):
            evidence_sets["item"].add(f"{order_id}:{int(order_item_id)}")
    
    # Build payment IDs: order_id:payment_sequential
    for _, row in order_payments.iterrows():
        order_id = str(row.get("order_id")) if pd.notna(row.get("order_id")) else None
        sequential = row.get("payment_sequential")
        if order_id and pd.notna(sequential):
            evidence_sets["payment"].add(f"{order_id}:{int(sequential)}")
    
    print(f"Loaded: {len(evidence_sets['order'])} orders, "
          f"{len(evidence_sets['item'])} items, "
          f"{len(evidence_sets['payment'])} payments, "
          f"{len(evidence_sets['seller'])} sellers")
    
    return evidence_sets


def parse_evidence_id(evidence_id: str) -> Tuple[str, str]:
    """Parse evidence ID into (type, id)."""
    if evidence_id.startswith("order:"):
        return "order", evidence_id[6:]
    elif evidence_id.startswith("item:"):
        parts = evidence_id[5:].split(":")
        if len(parts) >= 2:
            return "item", f"{parts[0]}:{parts[1]}"
        return "item", evidence_id[5:]
    elif evidence_id.startswith("payment:"):
        parts = evidence_id[8:].split(":")
        if len(parts) >= 2:
            return "payment", f"{parts[0]}:{parts[1]}"
        return "payment", evidence_id[8:]
    elif evidence_id.startswith("seller:"):
        return "seller", evidence_id[7:]
    elif evidence_id.startswith("policy:"):
        return "policy", evidence_id[7:]
    return "unknown", evidence_id


def verify_evidence_ids(evidence_sets: Dict[str, Set[str]]) -> None:
    """Verify all evidence IDs in output files."""
    output_dir = Path(__file__).parent / "output"
    output_files = sorted(output_dir.glob("EC_*.json"))
    
    total_invalid = 0
    case_results = []
    
    for output_file in output_files:
        case_id = output_file.stem
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        invalid_ids = []
        
        for evidence_id in data.get("evidence_ids", []):
            id_type, id_value = parse_evidence_id(evidence_id)
            
            if id_type == "policy":
                continue
            
            if id_type == "unknown":
                invalid_ids.append((evidence_id, "unknown type"))
                continue
            
            if id_type in evidence_sets:
                if id_value not in evidence_sets[id_type]:
                    invalid_ids.append((evidence_id, f"not found in {id_type} CSV"))
        
        if invalid_ids:
            total_invalid += len(invalid_ids)
            case_results.append({
                "case_id": case_id,
                "status": "FAIL",
                "invalid_count": len(invalid_ids),
                "invalid_ids": invalid_ids,
            })
        else:
            case_results.append({
                "case_id": case_id,
                "status": "PASS",
                "invalid_count": 0,
            })
    
    # Print results
    print("\n" + "=" * 70)
    print("EVIDENCE ID VERIFICATION RESULTS")
    print("=" * 70)
    
    fail_count = sum(1 for r in case_results if r["status"] == "FAIL")
    pass_count = len(case_results) - fail_count
    
    print(f"\nTotal: {len(case_results)} cases, {pass_count} passed, {fail_count} failed")
    print(f"Total invalid evidence IDs: {total_invalid}")
    
    if fail_count > 0:
        print("\nFailed cases:")
        for r in case_results:
            if r["status"] == "FAIL":
                print(f"\n  {r['case_id']} ({r['invalid_count']} invalid):")
                for eid, reason in r["invalid_ids"]:
                    print(f"    - {eid}: {reason}")


if __name__ == "__main__":
    evidence_sets = load_all_evidence_ids()
    verify_evidence_ids(evidence_sets)
