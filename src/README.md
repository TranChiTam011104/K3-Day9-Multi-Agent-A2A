# Source Code Module

This directory contains the infrastructure code for the multi-agent e-commerce dispute resolution system.

## Structure

```
src/
├── __init__.py        # Package exports
├── data_loader.py     # Load & cache CSV files
├── validators.py      # Validate output schema & evidence IDs
├── policy.py          # EC_POLICY_V1 business rules
├── output_writer.py   # Write JSON output files
└── trace_logger.py    # Trace execution for audit
```

## Usage

```python
from src import (
    load_all_csvs,
    get_order_with_details,
    apply_policy,
    build_output,
    write_output,
)

# Load all data
load_all_csvs()

# Get order details
order_data = get_order_with_details("order_id_here")

# Apply policy
result = apply_policy(
    order_status="delivered",
    payment_total=115.0,
    is_late_delivery=True,
    late_sellers=["seller_123"],
    on_time_sellers=[],
    payments_count=1,
    is_reconciled=True,
    freight_total=15.0,
)

# Build and write output
output = build_output(...)
write_output("EC_001", output)
```

## Running

```bash
# Using conda
conda activate env
python run.py

# Using run.bat (Windows)
run.bat

# Process single case
python run.py --case EC_001

# List all cases
python run.py --list-cases
```

## For Other Team Members

Người 2-5 sẽ sử dụng các module này để xử lý data của mình:

- **Người 2, 3** (Order/Seller): Dùng `data_loader.py` để lấy order details
- **Người 4, 5** (Payment/Delivery): Dùng `data_loader.py` + `analyze_delivery_timing()`
- **Người 6** (Coordinator): Dùng `policy.py` + `output_writer.py` để tổng hợp và xuất output
