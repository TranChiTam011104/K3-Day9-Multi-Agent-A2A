"""
Data Loader Module
Load và cache các CSV files từ Olist dataset.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# Global cache cho các DataFrames
_cache: Dict[str, pd.DataFrame] = {}


def load_csv(filename: str, use_cache: bool = True) -> pd.DataFrame:
    """
    Load một CSV file vào DataFrame.

    Args:
        filename: Tên file trong thư mục data/
        use_cache: Có dùng cache không

    Returns:
        DataFrame chứa dữ liệu
    """
    if use_cache and filename in _cache:
        logger.debug(f"Using cached: {filename}")
        return _cache[filename]

    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    df = pd.read_csv(filepath)
    _cache[filename] = df
    logger.info(f"Loaded {filename}: {len(df)} rows")
    return df


def load_all_csvs() -> Dict[str, pd.DataFrame]:
    """
    Load tất cả CSV files cần thiết.

    Returns:
        Dict với key = filename, value = DataFrame
    """
    files = [
        "olist_orders_dataset.csv",
        "olist_order_items_dataset.csv",
        "olist_order_payments_dataset.csv",
        "olist_order_reviews_dataset.csv",
        "olist_customers_dataset.csv",
        "olist_products_dataset.csv",
        "olist_sellers_dataset.csv",
        "olist_geolocation_dataset.csv",
        "product_category_name_translation.csv",
    ]

    result = {}
    for f in files:
        try:
            result[f] = load_csv(f)
        except FileNotFoundError:
            logger.warning(f"File not found: {f}")
            result[f] = pd.DataFrame()

    return result


def get_order_with_details(order_id: str) -> Dict[str, Any]:
    """
    Lấy thông tin chi tiết của một order.

    Args:
        order_id: Order ID cần tra cứu

    Returns:
        Dict chứa order info, items, payments, v.v.
    """
    orders = load_csv("olist_orders_dataset.csv")
    order_items = load_csv("olist_order_items_dataset.csv")
    order_payments = load_csv("olist_order_payments_dataset.csv")
    sellers = load_csv("olist_sellers_dataset.csv")

    # Filter order
    order_row = orders[orders["order_id"] == order_id]
    if order_row.empty:
        return {"error": f"Order {order_id} not found"}

    order = order_row.iloc[0].to_dict()

    # Get items
    items = order_items[order_items["order_id"] == order_id]
    items_list = items.to_dict("records")

    # Get payments
    payments = order_payments[order_payments["order_id"] == order_id]
    payments_list = payments.to_dict("records")

    # Get seller info
    seller_ids = items["seller_id"].unique().tolist()
    seller_info = sellers[sellers["seller_id"].isin(seller_ids)].to_dict("records")

    # Calculate totals
    item_total = items["price"].sum() if not items.empty else 0.0
    freight_total = items["freight_value"].sum() if not items.empty else 0.0
    payment_total = payments["payment_value"].sum() if not payments.empty else 0.0

    return {
        "order": order,
        "items": items_list,
        "items_count": len(items_list),
        "payments": payments_list,
        "payments_count": len(payments_list),
        "seller_ids": seller_ids,
        "seller_info": seller_info,
        "financials": {
            "item_total_brl": round(item_total, 2),
            "freight_total_brl": round(freight_total, 2),
            "payment_total_brl": round(payment_total, 2),
        },
    }


def analyze_delivery_timing(order_id: str) -> Dict[str, Any]:
    """
    Phân tích thời gian giao hàng.

    Args:
        order_id: Order ID cần phân tích

    Returns:
        Dict chứa delivery timing info
    """
    order_data = get_order_with_details(order_id)
    if "error" in order_data:
        return order_data

    order = order_data["order"]
    items = pd.DataFrame(order_data["items"])

    result = {
        "order_id": order_id,
        "order_status": order.get("order_status"),
        "estimated_delivery": order.get("order_estimated_delivery_date"),
        "delivered_carrier": order.get("order_delivered_carrier_date"),
        "delivered_customer": order.get("order_delivered_customer_date"),
        "shipping_limits": [],
        "is_late_delivery": False,
        "late_sellers": [],
        "on_time_sellers": [],
    }

    if not items.empty:
        # Get max shipping limit per seller
        for _, item in items.iterrows():
            seller_id = item["seller_id"]
            shipping_limit = item["shipping_limit_date"]
            delivered_carrier = order.get("order_delivered_carrier_date")

            result["shipping_limits"].append({
                "seller_id": seller_id,
                "shipping_limit_date": shipping_limit,
                "order_delivered_carrier_date": delivered_carrier,
            })

            # Check if seller handed off late
            if pd.notna(shipping_limit) and pd.notna(delivered_carrier):
                if delivered_carrier > shipping_limit:
                    result["late_sellers"].append(seller_id)
                else:
                    result["on_time_sellers"].append(seller_id)

    # Check if delivery is late (compare with estimated)
    if pd.notna(order.get("order_estimated_delivery_date")) and pd.notna(
        order.get("order_delivered_customer_date")
    ):
        result["is_late_delivery"] = (
            order["order_delivered_customer_date"] > order["order_estimated_delivery_date"]
        )

    return result


def check_payment_reconciliation(order_id: str, tolerance: float = 0.10) -> Dict[str, Any]:
    """
    Kiểm tra payment có khớp với item + freight không.

    Args:
        order_id: Order ID cần kiểm tra
        tolerance: Sai số cho phép (default 0.10 BRL)

    Returns:
        Dict chứa payment reconciliation info
    """
    order_data = get_order_with_details(order_id)
    if "error" in order_data:
        return order_data

    financials = order_data["financials"]
    payments_count = order_data["payments_count"]

    item_total = financials["item_total_brl"]
    freight_total = financials["freight_total_brl"]
    payment_total = financials["payment_total_brl"]

    expected_total = round(item_total + freight_total, 2)
    difference = round(payment_total - expected_total, 2)
    is_reconciled = abs(difference) <= tolerance

    return {
        "order_id": order_id,
        "payments_count": payments_count,
        "is_split_payment": payments_count >= 2,
        "item_total_brl": item_total,
        "freight_total_brl": freight_total,
        "expected_total_brl": expected_total,
        "payment_total_brl": payment_total,
        "difference_brl": difference,
        "is_reconciled": is_reconciled,
        "within_tolerance": abs(difference) <= tolerance,
    }


def clear_cache():
    """Xóa cache của các DataFrames."""
    global _cache
    _cache = {}
    logger.info("Cache cleared")


def preload_all_data():
    """Preload tất cả CSV files vào cache."""
    load_all_csvs()
    logger.info("All data preloaded into cache")
