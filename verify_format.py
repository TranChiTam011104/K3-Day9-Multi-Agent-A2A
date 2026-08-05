import json
import pandas as pd
from pathlib import Path

items = pd.read_csv('data/olist_order_items_dataset.csv')
payments = pd.read_csv('data/olist_order_payments_dataset.csv')

# Analyze a few outputs
for case_id in ['EC_001', 'EC_002', 'EC_004']:
    with open(f'output/{case_id}.json') as f:
        output = json.load(f)
    
    with open(f'input/{case_id}.json') as f:
        case = json.load(f)
    order_id = case['customer_request']['claimed_order_id']
    
    print(f'{case_id}: Order ID = {order_id}')
    
    # Check item IDs - format is {order_id}:{order_item_id}
    item_ids = output['affected_entities']['item_ids']
    print(f'  Item IDs from output: {item_ids}')
    actual_items = items[items['order_id'] == order_id]
    actual_item_ids = actual_items['order_item_id'].tolist()
    print(f'  Actual order_item_ids in CSV: {actual_item_ids}')
    
    # Check if all item_ids are valid
    for item_id in item_ids:
        parts = item_id.split(':')
        order_id_part = parts[0]
        item_seq = int(parts[1])
        if item_seq not in actual_item_ids:
            print(f'    INVALID: {item_id} - item_seq {item_seq} not in {actual_item_ids}')
    
    # Check payment IDs - format is {order_id}:{payment_sequential}
    payment_ids = output['affected_entities']['payment_ids']
    print(f'  Payment IDs from output: {payment_ids}')
    actual_payments = payments[payments['order_id'] == order_id]
    actual_payment_seqs = actual_payments['payment_sequential'].tolist()
    print(f'  Actual payment_sequentials in CSV: {actual_payment_seqs}')
    
    for pay_id in payment_ids:
        parts = pay_id.split(':')
        pay_seq = int(parts[1])
        if pay_seq not in actual_payment_seqs:
            print(f'    INVALID: {pay_id} - pay_seq {pay_seq} not in {actual_payment_seqs}')
    
    print()
