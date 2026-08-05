"""
Script kiểm tra và tổng hợp kết quả sau khi chạy xong 50 cases.
Chạy: python verify_results.py
"""
import json
import os
from pathlib import Path

OUTPUT_DIR = Path("output")
INPUT_DIR = Path("input")

# Collect all output files
output_files = sorted(OUTPUT_DIR.glob("EC_*.json"))
input_files = sorted(INPUT_DIR.glob("EC_*.json"))

print(f"Input cases:  {len(input_files)}")
print(f"Output files: {len(output_files)}")
print()

if len(output_files) < 50:
    missing = set(f.stem for f in input_files) - set(f.stem for f in output_files)
    print(f"Missing: {sorted(missing)}")
    print()

# Summarize results
issue_counts = {}
status_counts = {"action_required": 0, "no_action": 0}
total_refund = 0.0
errors = []

for f in output_files:
    try:
        with open(f) as fp:
            data = json.load(fp)

        issue = data["assessment"]["primary_issue"]
        status = data["assessment"]["case_status"]
        refund = data["financial_resolution"]["recommended_refund_brl"]
        confidence = data["assessment"]["confidence"]

        issue_counts[issue] = issue_counts.get(issue, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
        total_refund += refund

    except Exception as e:
        errors.append(f"{f.name}: {e}")

print("=== ISSUE DISTRIBUTION ===")
for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
    print(f"  {issue:<35} {count:>3} cases")

print()
print("=== CASE STATUS ===")
for status, count in status_counts.items():
    print(f"  {status:<25} {count:>3} cases")

print()
print(f"  Total recommended refunds: {total_refund:.2f} BRL")

if errors:
    print(f"\n=== ERRORS ({len(errors)}) ===")
    for e in errors:
        print(f"  {e}")
else:
    print(f"\n✓ All {len(output_files)} files valid JSON")
