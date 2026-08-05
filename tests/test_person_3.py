import pytest
import pandas as pd
import src.data_loader as data_loader
from src.data_loader import (
    get_order_with_details,
    analyze_delivery_timing,
    clear_cache
)

@pytest.fixture(autouse=True)
def setup_mock_data():
    """Tạo mock data cho các bảng để phục vụ test."""
    clear_cache()
    
    # Giả lập dữ liệu orders
    data_loader._cache["olist_orders_dataset.csv"] = pd.DataFrame([
        # Single seller, single item, on time
        {"order_id": "ORD_01", "order_status": "delivered", "order_delivered_carrier_date": "2018-05-10", "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-12"},
        # Single seller, multiple items, on time
        {"order_id": "ORD_02", "order_status": "delivered", "order_delivered_carrier_date": "2018-05-10", "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-12"},
        # Multiple sellers, all on time
        {"order_id": "ORD_03", "order_status": "delivered", "order_delivered_carrier_date": "2018-05-10", "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-12"},
        # Multiple sellers, 1 violates (late)
        {"order_id": "ORD_04", "order_status": "delivered", "order_delivered_carrier_date": "2018-05-12", "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-16"},
        # Multiple sellers, both violate
        {"order_id": "ORD_05", "order_status": "delivered", "order_delivered_carrier_date": "2018-05-13", "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-16"},
        # Carrier date == shipping limit date (on time)
        {"order_id": "ORD_06", "order_status": "delivered", "order_delivered_carrier_date": "2018-05-10", "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-12"},
        # Carrier date > shipping limit date (late)
        {"order_id": "ORD_07", "order_status": "delivered", "order_delivered_carrier_date": "2018-05-11", "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-16"},
        # Missing carrier date
        {"order_id": "ORD_08", "order_status": "delivered", "order_delivered_carrier_date": None, "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-16"},
        # Missing shipping limit date (handled in items)
        {"order_id": "ORD_09", "order_status": "delivered", "order_delivered_carrier_date": "2018-05-11", "order_estimated_delivery_date": "2018-05-15", "order_delivered_customer_date": "2018-05-16"},
        # Canceled order with weird cases and space
        {"order_id": "ORD_10", "order_status": " CANCELED ", "order_delivered_carrier_date": None, "order_estimated_delivery_date": None, "order_delivered_customer_date": None},
        # Unavailable order
        {"order_id": "ORD_11", "order_status": "UNAVAILABLE", "order_delivered_carrier_date": None, "order_estimated_delivery_date": None, "order_delivered_customer_date": None},
    ])

    data_loader._cache["olist_order_items_dataset.csv"] = pd.DataFrame([
        # ORD_01
        {"order_id": "ORD_01", "order_item_id": 1, "seller_id": "S1", "shipping_limit_date": "2018-05-11", "price": 50.0, "freight_value": 10.0},
        
        # ORD_02 - multi items, single seller
        {"order_id": "ORD_02", "order_item_id": 1, "seller_id": "S2", "shipping_limit_date": "2018-05-11", "price": 30.0, "freight_value": 5.0},
        {"order_id": "ORD_02", "order_item_id": 3, "seller_id": "S2", "shipping_limit_date": "2018-05-11", "price": 40.0, "freight_value": 7.0},
        
        # ORD_03 - multi sellers, both on time (carrier: 05-10, limits: 05-11)
        {"order_id": "ORD_03", "order_item_id": 1, "seller_id": "S3", "shipping_limit_date": "2018-05-11", "price": 10.0, "freight_value": 2.0},
        {"order_id": "ORD_03", "order_item_id": 2, "seller_id": "S4", "shipping_limit_date": "2018-05-11", "price": 20.0, "freight_value": 3.0},
        
        # ORD_04 - multi sellers, 1 violates (carrier: 05-12)
        # S5 limit: 05-13 (on time), S6 limit: 05-11 (late)
        {"order_id": "ORD_04", "order_item_id": 1, "seller_id": "S5", "shipping_limit_date": "2018-05-13", "price": 10.0, "freight_value": 2.0},
        {"order_id": "ORD_04", "order_item_id": 2, "seller_id": "S6", "shipping_limit_date": "2018-05-11", "price": 20.0, "freight_value": 3.0},
        
        # ORD_05 - multi sellers, both violate (carrier: 05-13)
        # S7 limit: 05-11, S8 limit: 05-12
        {"order_id": "ORD_05", "order_item_id": 1, "seller_id": "S7", "shipping_limit_date": "2018-05-11", "price": 10.0, "freight_value": 2.0},
        {"order_id": "ORD_05", "order_item_id": 2, "seller_id": "S8", "shipping_limit_date": "2018-05-12", "price": 20.0, "freight_value": 3.0},
        
        # ORD_06 - carrier = limit (carrier: 05-10, limit: 05-10) -> on time
        {"order_id": "ORD_06", "order_item_id": 1, "seller_id": "S1", "shipping_limit_date": "2018-05-10", "price": 50.0, "freight_value": 10.0},
        
        # ORD_07 - carrier > limit (carrier: 05-11, limit: 05-10) -> late
        {"order_id": "ORD_07", "order_item_id": 1, "seller_id": "S1", "shipping_limit_date": "2018-05-10", "price": 50.0, "freight_value": 10.0},
        
        # ORD_08 - missing carrier date -> assume not late for seller
        {"order_id": "ORD_08", "order_item_id": 1, "seller_id": "S1", "shipping_limit_date": "2018-05-10", "price": 50.0, "freight_value": 10.0},
        
        # ORD_09 - missing shipping limit date -> assume not late for seller
        {"order_id": "ORD_09", "order_item_id": 1, "seller_id": "S1", "shipping_limit_date": None, "price": 50.0, "freight_value": 10.0},
    ])

    data_loader._cache["olist_order_payments_dataset.csv"] = pd.DataFrame(columns=[
        "order_id", "payment_sequential", "payment_value"
    ])
    
    data_loader._cache["olist_sellers_dataset.csv"] = pd.DataFrame([
        {"seller_id": f"S{i}"} for i in range(1, 9)
    ])

    yield
    clear_cache()


def test_missing_order():
    """Test xử lý khi order_id không tồn tại."""
    result = get_order_with_details("ORD_NOT_EXIST")
    assert "error" in result
    
def test_order_status_normalization():
    """Test order status được xử lý lowercase và strip (CANCELED, UNAVAILABLE)."""
    # CANCELED
    res = get_order_with_details("ORD_10")
    assert res["order"]["order_status"] == "canceled"
    
    # UNAVAILABLE
    res2 = get_order_with_details("ORD_11")
    assert res2["order"]["order_status"] == "unavailable"

def test_missing_seller_record():
    """Test item có seller_id không tồn tại trong sellers.csv."""
    # S9 doesn't exist in sellers dataset
    data_loader._cache["olist_order_items_dataset.csv"].loc[len(data_loader._cache["olist_order_items_dataset.csv"])] = {
        "order_id": "ORD_01", "order_item_id": 99, "seller_id": "S9", "shipping_limit_date": "2018-05-11", "price": 10.0, "freight_value": 5.0
    }
    res = get_order_with_details("ORD_01")
    assert "S9" in res["seller_ids"]
    assert len(res["seller_info"]) == 1 # Only S1 info found, not S9

def test_freight_total_multiple_items_and_no_double_join():
    """Test tính freight total, check không double data. Và kiểm tra item ids thực tế."""
    res = get_order_with_details("ORD_02")
    assert res["financials"]["freight_total_brl"] == 12.0 # 5.0 + 7.0
    assert res["items_count"] == 2
    
    # Check evidence format with real order_item_id (1 and 3)
    item_ids = [i["order_item_id"] for i in res["items"]]
    assert 1 in item_ids
    assert 3 in item_ids
    assert 2 not in item_ids

def test_evidence_unique():
    """Test evidence ID unique and seller evaluated properly."""
    res = analyze_delivery_timing("ORD_02")
    assert res["on_time_sellers"] == ["S2"]
    assert res["late_sellers"] == []
    
def test_carrier_equal_limit():
    """Test carrier date = shipping limit -> on time."""
    res = analyze_delivery_timing("ORD_06")
    assert res["late_sellers"] == []
    assert res["on_time_sellers"] == ["S1"]

def test_carrier_after_limit():
    """Test carrier date > shipping limit -> late."""
    res = analyze_delivery_timing("ORD_07")
    assert res["late_sellers"] == ["S1"]
    assert res["on_time_sellers"] == []

def test_missing_carrier_date():
    """Test missing carrier date."""
    res = analyze_delivery_timing("ORD_08")
    assert res["late_sellers"] == []
    assert res["on_time_sellers"] == []
    
def test_missing_shipping_limit():
    """Test missing shipping limit date."""
    res = analyze_delivery_timing("ORD_09")
    assert res["late_sellers"] == []
    assert res["on_time_sellers"] == []

def test_multiple_sellers_all_on_time():
    """Nhiều seller đều đúng hạn."""
    res = analyze_delivery_timing("ORD_03")
    assert set(res["on_time_sellers"]) == {"S3", "S4"}
    assert res["late_sellers"] == []

def test_multiple_sellers_one_late():
    """Nhiều seller, chỉ một vi phạm."""
    res = analyze_delivery_timing("ORD_04")
    assert res["late_sellers"] == ["S6"]
    assert res["on_time_sellers"] == ["S5"]

def test_multiple_sellers_both_late():
    """Nhiều seller, cùng vi phạm."""
    res = analyze_delivery_timing("ORD_05")
    assert set(res["late_sellers"]) == {"S7", "S8"}
    assert res["on_time_sellers"] == []

@pytest.mark.parametrize("order_id,expected_late,expected_on_time", [
    ("ORD_01", [], ["S1"]),
    ("ORD_02", [], ["S2"]),
    ("ORD_03", [], ["S3", "S4"]),
    ("ORD_04", ["S6"], ["S5"]),
    ("ORD_05", ["S7", "S8"], []),
    ("ORD_06", [], ["S1"]),
    ("ORD_07", ["S1"], []),
    ("ORD_08", [], []),
    ("ORD_09", [], []),
])
def test_all_15_cases_parametrized(order_id, expected_late, expected_on_time):
    """Parametrized test for multiple requirements."""
    res = analyze_delivery_timing(order_id)
    assert set(res["late_sellers"]) == set(expected_late)
    assert set(res["on_time_sellers"]) == set(expected_on_time)
