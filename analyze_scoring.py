"""
Detailed scoring analysis for each case.
"""

import json
from pathlib import Path
from collections import Counter

def analyze_case(case_id: str, output: dict) -> dict:
    """Analyze one case for scoring components."""
    results = {
        "case_id": case_id,
        "has_confidence": output["assessment"].get("confidence", 0) > 0,
        "has_primary_issue": bool(output["assessment"].get("primary_issue")),
        "affected_entities": {
            "order_ids": len(output["affected_entities"].get("order_ids", [])),
            "item_ids": len(output["affected_entities"].get("item_ids", [])),
            "seller_ids": len(output["affected_entities"].get("seller_ids", [])),
            "payment_ids": len(output["affected_entities"].get("payment_ids", [])),
        },
        "root_causes": len(output["root_cause_analysis"].get("ranked_causes", [])),
        "responsible_parties": len(output["root_cause_analysis"].get("responsible_parties", [])),
        "evidence_ids": len(output.get("evidence_ids", [])),
        "has_financials": all(k in output["financial_resolution"] for k in ["item_total_brl", "freight_total_brl", "payment_total_brl", "recommended_refund_brl"]),
        "resolution_actions": len(output.get("resolution_actions", [])),
    }
    return results

def main():
    output_dir = Path("output")
    
    all_results = []
    for i in range(1, 51):
        case_id = f"EC_{i:03d}"
        output_file = output_dir / f"{case_id}.json"
        
        if not output_file.exists():
            print(f"Missing: {case_id}")
            continue
            
        with open(output_file, "r") as f:
            output = json.load(f)
        
        results = analyze_case(case_id, output)
        all_results.append(results)
    
    # Summary
    print("=" * 70)
    print("SCORING COMPONENT ANALYSIS")
    print("=" * 70)
    
    total = len(all_results)
    print(f"\nTotal cases: {total}")
    
    # Check each component
    print("\n--- Assessment ---")
    has_confidence = sum(1 for r in all_results if r["has_confidence"])
    has_primary_issue = sum(1 for r in all_results if r["has_primary_issue"])
    print(f"Cases with confidence > 0: {has_confidence}/{total}")
    print(f"Cases with primary_issue: {has_primary_issue}/{total}")
    
    print("\n--- Affected Entities ---")
    order_ids = sum(r["affected_entities"]["order_ids"] for r in all_results)
    item_ids = sum(r["affected_entities"]["item_ids"] for r in all_results)
    seller_ids = sum(r["affected_entities"]["seller_ids"] for r in all_results)
    payment_ids = sum(r["affected_entities"]["payment_ids"] for r in all_results)
    print(f"Total order_ids: {order_ids} (avg: {order_ids/total:.1f})")
    print(f"Total item_ids: {item_ids} (avg: {item_ids/total:.1f})")
    print(f"Total seller_ids: {seller_ids} (avg: {seller_ids/total:.1f})")
    print(f"Total payment_ids: {payment_ids} (avg: {payment_ids/total:.1f})")
    
    print("\n--- Root Causes & Responsible Parties ---")
    root_causes = sum(r["root_causes"] for r in all_results)
    resp_parties = sum(r["responsible_parties"] for r in all_results)
    print(f"Total root causes: {root_causes} (avg: {root_causes/total:.1f})")
    print(f"Total responsible parties: {resp_parties} (avg: {resp_parties/total:.1f})")
    
    print("\n--- Evidence IDs ---")
    evidence_ids = sum(r["evidence_ids"] for r in all_results)
    print(f"Total evidence_ids: {evidence_ids} (avg: {evidence_ids/total:.1f})")
    min_evidence = min(r["evidence_ids"] for r in all_results)
    max_evidence = max(r["evidence_ids"] for r in all_results)
    print(f"Range: {min_evidence} - {max_evidence}")
    
    print("\n--- Financial Resolution ---")
    has_financials = sum(1 for r in all_results if r["has_financials"])
    print(f"Cases with complete financials: {has_financials}/{total}")
    
    print("\n--- Resolution Actions ---")
    actions = sum(r["resolution_actions"] for r in all_results)
    print(f"Total resolution_actions: {actions} (avg: {actions/total:.1f})")
    
    # Count primary issues
    print("\n--- Primary Issue Distribution ---")
    issues = []
    for i in range(1, 51):
        output_file = output_dir / f"EC_{i:03d}.json"
        with open(output_file, "r") as f:
            output = json.load(f)
        issues.append(output["assessment"]["primary_issue"])
    
    issue_counts = Counter(issues)
    for issue, count in issue_counts.most_common():
        print(f"  {issue}: {count}")

if __name__ == "__main__":
    main()
