import pandas as pd

items = pd.read_csv('data/olist_order_items_dataset.csv')
payments = pd.read_csv('data/olist_order_payments_dataset.csv')

unavailable_orders = [
    '9a31fd9d697e9670777501f720773fd9',  # EC_005
    '2636a02ee7de9590df86a4c24b739c49',  # EC_011
]

for order_id in unavailable_orders:
    order_items = items[items['order_id'] == order_id]
    order_payments = payments[payments['order_id'] == order_id]
    
    print(f'Order: {order_id}')
    print(f'  Items: {len(order_items)} rows')
    print(f'  Payments: {len(order_payments)} rows')
    if not order_items.empty:
        print(f'  Item IDs: {order_items["order_item_id"].tolist()}')
        print(f'  Sellers: {order_items["seller_id"].unique().tolist()}')
    else:
        print('  No items found!')
    print()
