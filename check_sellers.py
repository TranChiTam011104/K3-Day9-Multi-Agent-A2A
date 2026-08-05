import json
from pathlib import Path

output_dir = Path('output')
for i in range(1, 51):
    case_id = f"EC_{i:03d}"
    with open(output_dir / f"{case_id}.json") as f:
        data = json.load(f)
    if not data['affected_entities']['seller_ids']:
        print(f"{case_id}: issue={data['assessment']['primary_issue']}, items={len(data['affected_entities']['item_ids'])}")
