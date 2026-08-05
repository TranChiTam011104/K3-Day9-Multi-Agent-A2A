import json
import pandas as pd

orders = pd.read_csv('data/olist_orders_dataset.csv')
items = pd.read_csv('data/olist_order_items_dataset.csv')

print('LATE DELIVERY CASES ANALYSIS')
print('=' * 80)

late_cases = []
for i in range(1, 51):
    case_id = f'EC_{i:03d}'
    with open(f'output/{case_id}.json') as f:
        output = json.load(f)
    with open(f'input/{case_id}.json') as f:
        case = json.load(f)
    
    order_id = case['customer_request']['claimed_order_id']
    output_issue = output['assessment']['primary_issue']
    
    if output_issue in ['late_delivery_seller', 'late_delivery_logistics']:
        order = orders[orders['order_id'] == order_id].iloc[0]
        order_items = items[items['order_id'] == order_id]
        
        carrier_date = pd.to_datetime(order.get('order_delivered_carrier_date'), errors='coerce')
        estimated = pd.to_datetime(order.get('order_estimated_delivery_date'), errors='coerce')
        delivered = pd.to_datetime(order.get('order_delivered_customer_date'), errors='coerce')
        
        seller_status = []
        for _, item in order_items.iterrows():
            sl = pd.to_datetime(item['shipping_limit_date'], errors='coerce')
            if pd.notna(carrier_date) and pd.notna(sl):
                if carrier_date > sl:
                    seller_status.append('LATE')
                else:
                    seller_status.append('ON_TIME')
            else:
                seller_status.append('UNKNOWN')
        
        late_cases.append({
            'case_id': case_id,
            'issue': output_issue,
            'seller_status': seller_status,
            'has_late_sellers': 'LATE' in seller_status,
            'has_on_time_sellers': 'ON_TIME' in seller_status,
        })

mismatches = []
for lc in late_cases:
    gt_issue = 'late_delivery_seller' if lc['has_late_sellers'] else 'late_delivery_logistics'
    if lc['issue'] != gt_issue:
        mismatches.append({
            'case_id': lc['case_id'],
            'output': lc['issue'],
            'expected': gt_issue,
            'seller_status': lc['seller_status']
        })

print(f'Total late cases: {len(late_cases)}')
print(f'Mismatches found: {len(mismatches)}')

if mismatches:
    print('\nMISMATCHES:')
    for m in mismatches:
        print(f"  {m['case_id']}: output={m['output']}, expected={m['expected']}")
        print(f"    Seller status: {m['seller_status']}")
