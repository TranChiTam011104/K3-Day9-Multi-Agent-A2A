import pandas as pd
import json

orders = pd.read_csv('data/olist_orders_dataset.csv')
items = pd.read_csv('data/olist_order_items_dataset.csv')
payments = pd.read_csv('data/olist_order_payments_dataset.csv')
sellers = pd.read_csv('data/olist_sellers_dataset.csv')

print('CANCELED ORDERS ANALYSIS')
print('=' * 80)

for i in range(1, 51):
    case_id = f'EC_{i:03d}'
    with open(f'output/{case_id}.json') as f:
        output = json.load(f)
    with open(f'input/{case_id}.json') as f:
        case = json.load(f)
    
    order_id = case['customer_request']['claimed_order_id']
    issue = output['assessment']['primary_issue']
    
    if issue == 'canceled_order_paid':
        order_items = items[items['order_id'] == order_id]
        order_payments = payments[payments['order_id'] == order_id]
        order_sellers = sellers[sellers['seller_id'].isin(order_items['seller_id'].unique())]
        
        print(f'{case_id}:')
        print(f'  Items: {len(order_items)} rows')
        print(f'  Payments: {len(order_payments)} rows')
        print(f'  Sellers: {len(order_sellers)} rows')
        print(f'  Evidence IDs: {len(output["evidence_ids"])} - {output["evidence_ids"]}')
        
        # Check financial
        fin = output['financial_resolution']
        print(f'  Financial: item={fin["item_total_brl"]}, freight={fin["freight_total_brl"]}, payment={fin["payment_total_brl"]}, refund={fin["recommended_refund_brl"]}')
        print()
