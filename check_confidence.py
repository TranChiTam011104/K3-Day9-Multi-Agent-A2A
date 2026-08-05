import json
from collections import defaultdict

print('CONFIDENCE ANALYSIS')
print('=' * 80)

confidences = []
for i in range(1, 51):
    case_id = f'EC_{i:03d}'
    with open(f'output/{case_id}.json') as f:
        output = json.load(f)
    
    issue = output['assessment']['primary_issue']
    conf = output['assessment']['confidence']
    
    confidences.append({
        'case_id': case_id,
        'issue': issue,
        'confidence': conf
    })

# Group by issue type
by_issue = defaultdict(list)
for c in confidences:
    by_issue[c['issue']].append(c)

for issue, cases in by_issue.items():
    avg_conf = sum(c['confidence'] for c in cases) / len(cases)
    confs = [c['confidence'] for c in cases]
    unique_confs = set(confs)
    print(f'{issue}: {len(cases)} cases, avg_conf={avg_conf:.2f}, values={unique_confs}')

print()
print('Cases with confidence != 1.0:')
for c in confidences:
    if c['confidence'] != 1.0:
        print(f"  {c['case_id']}: {c['issue']} -> {c['confidence']}")
