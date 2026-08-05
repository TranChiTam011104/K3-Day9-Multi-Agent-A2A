# PHÂN CÔNG CÔNG VIỆC

## Tổng quan bài toán
- **50 case** khiếu nại khách hàng (EC_001 → EC_050)
- **9 file CSV** dữ liệu Olist để join và phân tích
- **6 quy tắc nghiệp vụ** để xác định primary issue
- **Output schema** chuẩn cho mỗi case

---

## PHÂN CÔNG CHO 6 NGƯỜI

### Người 1: ARCHITECTURE & INFRASTRUCTURE
**Phạm vi:** Toàn bộ hệ thống

| Nhiệm vụ | Chi tiết |
|----------|----------|
| Thiết kế `architecture.md` | Sơ đồ agent, vai trò, quyền truy cập, luồng handoff |
| Setup project structure | Tạo thư mục `data/`, `input/`, `output/`, `src/` |
| Chuẩn hóa data loader | Hàm load/join 9 CSV, cache reusable DataFrames |
| Tạo shared utilities | Schema validation, evidence ID generator, policy checker |
| Viết `metadata.json` | Model, parameter size, framework, runtime |

**Output bắt buộc:**
- `architecture.md`
- `metadata.json`
- `src/utils.py` (data loader, validators)

**Độc lập:** Có thể làm TRƯỚC hoàn toàn, không phụ thuộc ai.

---

### Người 2: ORDER & SELLER PROCESSING (EC_001 - EC_010, EC_021 - EC_025)
**Phạm vi:** 15 case đầu tiên

| Nhiệm vụ | Chi tiết |
|----------|----------|
| Load orders.csv + order_items.csv + sellers.csv | Join theo order_id, seller_id |
| Kiểm tra order_status | canceled, unavailable, delivered, ... |
| Kiểm tra shipping_limit_date | So sánh với order_delivered_carrier_date |
| Xác định seller vi phạm | Nếu có nhiều seller → mỗi seller check riêng |
| Trích xuất item_ids, seller_ids | Format: `item:<order_id>:<order_item_id>` |
| Tính freight_total_brl | Sum freight_value từ order_items |

**Evidence IDs cần thu thập:**
```
order:<order_id>
item:<order_id>:1, item:<order_id>:2, ...
seller:<seller_id>
```

**Case list:**
```
EC_001, EC_002, EC_003, EC_004, EC_005,
EC_006, EC_007, EC_008, EC_009, EC_010,
EC_021, EC_022, EC_023, EC_024, EC_025
```

---

### Người 3: ORDER & SELLER PROCESSING (EC_011 - EC_020, EC_026 - EC_030)
**Phạm vi:** 15 case tiếp theo

| Nhiệm vụ | Chi tiết |
|----------|----------|
| Load orders.csv + order_items.csv + sellers.csv | Join theo order_id, seller_id |
| Kiểm tra order_status | canceled, unavailable, delivered, ... |
| Kiểm tra shipping_limit_date | So sánh với order_delivered_carrier_date |
| Xác định seller vi phạm | Nếu có nhiều seller → mỗi seller check riêng |
| Trích xuất item_ids, seller_ids | Format: `item:<order_id>:<order_item_id>` |
| Tính freight_total_brl | Sum freight_value từ order_items |

**Evidence IDs cần thu thập:**
```
order:<order_id>
item:<order_id>:1, item:<order_id>:2, ...
seller:<seller_id>
```

**Case list:**
```
EC_011, EC_012, EC_013, EC_014, EC_015,
EC_016, EC_017, EC_018, EC_019, EC_020,
EC_026, EC_027, EC_028, EC_029, EC_030
```

---

### Người 4: PAYMENT & DELIVERY ANALYSIS (EC_031 - EC_040)
**Phạm vi:** 10 case giữa

| Nhiệm vụ | Chi tiết |
|----------|----------|
| Load order_payments.csv | Tính tổng payment_value |
| Kiểm tra split payment | Có ≥2 payment rows? |
| Load orders.csv | Lấy estimated_delivery_date, delivered_customer_date |
| So sánh delivery vs estimate | Giao có trễ không? |
| Tính item_total_brl | Sum price * qty từ order_items |
| Verify payment = item + freight? | Sai số cho phép 0.10 BRL |

**Evidence IDs cần thu thập:**
```
payment:<order_id>:1, payment:<order_id>:2, ...
order:<order_id>
```

**Case list:**
```
EC_031, EC_032, EC_033, EC_034, EC_035,
EC_036, EC_037, EC_038, EC_039, EC_040
```

---

### Người 5: PAYMENT & DELIVERY ANALYSIS (EC_041 - EC_050)
**Phạm vi:** 10 case cuối

| Nhiệm vụ | Chi tiết |
|----------|----------|
| Load order_payments.csv | Tính tổng payment_value |
| Kiểm tra split payment | Có ≥2 payment rows? |
| Load orders.csv | Lấy estimated_delivery_date, delivered_customer_date |
| So sánh delivery vs estimate | Giao có trễ không? |
| Tính item_total_brl | Sum price * qty từ order_items |
| Verify payment = item + freight? | Sai số cho phép 0.10 BRL |

**Evidence IDs cần thu thập:**
```
payment:<order_id>:1, payment:<order_id>:2, ...
order:<order_id>
```

**Case list:**
```
EC_041, EC_042, EC_043, EC_044, EC_045,
EC_046, EC_047, EC_048, EC_049, EC_050
```

---

### Người 6: POLICY APPLICATION & OUTPUT GENERATION (Tất cả 50 case)
**Phạm vi:** Tổng hợp từ Người 2-5, áp dụng policy và viết output

| Nhiệm vụ | Chi tiết |
|----------|----------|
| Áp dụng EC_POLICY_V1 | Theo thứ tự ưu tiên |
| Xác định primary_issue | 6 loại issue có trọng số ưu tiên |
| Xác định responsible_party | platform / seller / logistics_provider |
| Tính recommended_refund_brl | Theo bảng refund rules |
| Set case_status | action_required / no_action |
| Set confidence | [0, 1] |
| Verify all evidence IDs | Format đúng, tồn tại trong CSV |
| Validate output schema | Trước khi ghi file |
| Viết 50 file JSON vào `output/` | EC_001.json → EC_050.json |

**Quy tắc policy (thứ tự ưu tiên):**

| Priority | Issue | Điều kiện | Responsible | Refund |
|----------|-------|-----------|-------------|--------|
| 1 | `canceled_order_paid` | status=canceled, payment>0 | platform | Tổng payment |
| 2 | `unavailable_order_paid` | status=unavailable, payment>0 | platform | Tổng payment |
| 3 | `late_delivery_seller` | giao sau estimate + carrier nhận sau limit | seller | freight |
| 4 | `late_delivery_logistics` | giao sau estimate + carrier nhận không muộn hơn limit | logistics | freight |
| 5 | `valid_split_payment` | ≥2 payment rows, tổng khớp | - | 0 |
| 6 | `unsupported_late_claim` | giao không trễ, payment khớp | - | 0 |

---

## LUỒNG LÀM VIỆC

```
[Timeline]
9h00-9h30: Người 1 setup infrastructure
          ↓
9h30-12h00: Tất cả 6 người làm song song
   ├── Người 2: EC_001-010, EC_021-025 (Order/Seller)
   ├── Người 3: EC_011-020, EC_026-030 (Order/Seller)
   ├── Người 4: EC_031-040 (Payment/Delivery)
   ├── Người 5: EC_041-050 (Payment/Delivery)
   └── Người 6: Tổng hợp + Policy + Output (sau khi 2-5 xong)
          ↓
12h00-12h30: Người 6 hoàn thành 50 output
          ↓
12h30: Nén output/ → submit.zip
```

---

## SƠ ĐỒ PHÂN CÔNG

```
┌─────────────────────────────────────────────────────────────┐
│                    NGƯỜI 1: ARCHITECT                        │
│         architecture.md, metadata.json, src/utils.py        │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         ↓               ↓               ↓               ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  NGƯỜI 2    │ │  NGƯỜI 3    │ │  NGƯỜI 4    │ │  NGƯỜI 5    │
│  Order/     │ │  Order/     │ │  Payment/   │ │  Payment/   │
│  Seller     │ │  Seller     │ │  Delivery    │ │  Delivery   │
│ EC_001-025  │ │ EC_011-030  │ │ EC_031-040   │ │ EC_041-050  │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │               │
       └───────────────┼───────────────┼───────────────┘
                       ↓
              ┌─────────────────┐
              │    NGƯỜI 6      │
              │   Coordinator   │
              │ Policy + Output │
              │   50 files      │
              └─────────────────┘
```

---

## QUY TẮC LÀM VIỆC

### Người 2-5 (Data Processing)
1. Mỗi người làm CHỦ TRÊN case list của mình
2. Không đụng case của người khác
3. Khi xong, báo cho Người 6 qua commit/chat
4. Ghi intermediate results vào thư mục riêng: `data/processed/person_X/`

### Người 6 (Coordinator & Output)
1. Đợi data từ Người 2-5
2. Merge data, áp dụng policy
3. Validate và write output
4. Cuối cùng: nén `output/` → `submit.zip`

### Người 1 (Architecture)
1. Hoàn thành TRƯỚC để Người 2-6 có base code
2. Hỗ trợ debug nếu cần trong quá trình làm

---

## CHECKLIST TRƯỚC KHI SUBMIT

- [x] `output/EC_001.json` → `output/EC_050.json` (đủ 50 file)
- [x] `architecture.md` ở root
- [x] `metadata.json` ở root
- [x] `individual_5SoCuoiMHV_HoVaTen.md` ở root (mỗi người viết)
- [x] `trace.jsonl` ghi lại execution
- [x] Source code đã commit lên repo
- [x] File `.env` KHÔNG commit (chứa API key)
- [x] Nén `output/` thành zip (chỉ output, không chứa code)
