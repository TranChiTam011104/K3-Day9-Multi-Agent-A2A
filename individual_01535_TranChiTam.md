# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                       |
| --------------- | ------------------------------ |
| Họ và tên       | Trần Chí Tâm                   |
| MSSV            | 2A202601535                    |
| Khóa/Lớp        | K3                             |
| Vai trò chính   | Architecture & Infrastructure  |
| Ngày hoàn thành | 2026-08-05                     |

---

## 2. Vai trò và phạm vi công việc

### Người 1: Architecture & Infrastructure (Hoàn thành)

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ---------------- | ----------- |
| Thiết kế hệ thống | `architecture.md` | Yêu cầu bài toán | Sơ đồ agent, luồng A2A | Hoàn thành |
| Project structure | `data/`, `input/`, `output/`, `src/` | - | Thư mục rỗng sẵn sàng | Hoàn thành |
| Data loader | `src/data_loader.py` | 9 CSV files | DataFrame cached, join functions | Hoàn thành |
| Validators | `src/validators.py` | Output JSON | Schema validation, evidence ID check | Hoàn thành |
| Policy engine | `src/policy.py` | Case data | EC_POLICY_V1 rules | Hoàn thành |
| Output writer | `src/output_writer.py` | Validated output | JSON files | Hoàn thành |
| Trace logger | `src/trace_logger.py` | Execution events | `trace.jsonl` | Hoàn thành |
| Metadata | `metadata.json` | - | Model info, team | Hoàn thành |
| Data verification | 9 CSV files | Kaggle dataset | 9 files verified in `data/` | Hoàn thành |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ----------------- | ---------------|
| Thiết kế multi-agent architecture | `architecture.md` | 6 agent roles, 10 sections | `type architecture.md` |
| Chuẩn hóa data loading với caching | `src/data_loader.py` | `load_csv()`, `join_orders_with_items()` | Python import test |
| Triển khai policy checker | `src/policy.py` | 6 priority rules, refund calculation | `python -c "from src.policy import ...` |
| Schema validation | `src/validators.py` | 10 evidence ID formats | `python -c "from src.validators import ...` |
| Output JSON writer | `src/output_writer.py` | Standardized JSON schema | `python -c "from src.output_writer import ...` |
| Execution trace logger | `src/trace_logger.py` | `trace.jsonl` for debugging | `python -c "from src.trace_logger import ...` |
| Download Kaggle dataset | `data/*.csv` | 9 files verified (total ~121MB) | `dir data\*.csv` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### 4.1 Data Loader Architecture

**Vấn đề cần giải quyết:**
Cần load và cache 9 CSV files để tránh đọc lại nhiều lần trong quá trình xử lý 50 cases. Mỗi CSV có thể lên đến 62MB (geolocation), cần tối ưu memory.

**Cách triển khai:**
- Sử dụng `functools.lru_cache` để cache DataFrames sau khi load
- Implement lazy loading - chỉ load khi cần
- Join functions với keys rõ ràng để tránh ambiguous joins
- Schema validation ngay khi load để fail early

**Input, output và contract:**

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | 9 CSV files trong `data/` |
| Output | Pandas DataFrames cached in memory |
| Module phụ thuộc | `pandas`, `src/__init__.py` |
| Module sử dụng output | `src/policy.py`, `src/validators.py`, `main.py` |
| Điều kiện lỗi cần xử lý | File not found, malformed CSV, missing columns |

**Cách xác minh:**

```bash
python -c "from src.data_loader import load_csv, load_orders; df = load_orders(); print(f'Orders: {len(df)}')"
```

- **Kết quả mong đợi:** DataFrame với orders loaded
- **Kết quả thực tế:** Verified ✅
- **Artifact/log:** `src/data_loader.py`

### 4.2 Policy Engine

**Vấn đề cần giải quyết:**
Xác định primary issue và tính refund dựa trên 6 rules có thứ tự ưu tiên. Cần đảm bảo rules được apply đúng thứ tự.

**Cách triển khai:**
- Priority-based rule engine với `while` loop
- Mỗi rule check conditions theo thứ tự ưu tiên
- Khi match, dừng và return kết quả
- Refund calculation dựa trên table lookup

**Input, output và contract:**

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | Order data, payment data, delivery dates |
| Output | `primary_issue`, `responsible_party`, `recommended_refund_brl` |
| Module phụ thuộc | `src/data_loader.py` |
| Module sử dụng output | `src/output_writer.py` |
| Điều kiện lỗi cần xử lý | No matching rule (fallback to `unsupported_late_claim`) |

**Cách xác minh:**

```bash
python -c "from src.policy import apply_policy; result = apply_policy({'order_status': 'canceled', 'payment_total': 100}); print(result)"
```

- **Kết quả mong đợi:** `primary_issue='canceled_order_paid'`, `refund=100`
- **Kết quả thực tế:** Verified ✅
- **Artifact/log:** `src/policy.py`

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Thiết kế data loading strategy - load tất cả CSV vào memory hay lazy load per case?
- **Các phương án đã cân nhắc:**
  1. Load all CSVs at startup: Đơn giản, nhanh khi xử lý nhiều cases
  2. Lazy load per case: Tiết kiệm memory, chậm hơn cho nhiều cases
- **Phương án đã chọn:** Kết hợp - Load nhưng với caching (lru_cache)
- **Lý do:** Balance giữa performance (không đọc lại CSV) và memory (chỉ load khi cần). Với 50 cases, caching tối ưu hơn lazy load vì mỗi CSV được access nhiều lần.
- **Bằng chứng quyết định phù hợp:** 9 CSV files (total 121MB) fit comfortably in memory; Người 2-5 đều cần access data nhiều lần

---

## 6. Một lỗi hoặc blocker đã xử lý

### Blocker đã xử lý: CSV Files Missing

- **Triệu chứng/lỗi nguyên văn:** `data/` folder chỉ có 2/9 files (sellers + translation)
- **Lệnh hoặc bước tái hiện:** `dir data\*.csv` → Missing 7 files
- **Nguyên nhân gốc:** Kaggle dataset chưa được download đầy đủ
- **Cách xử lý:** Download Brazilian E-commerce dataset từ https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- **Cách xác minh sau khi sửa:** `dir data\*.csv` → 9 files, total ~121MB
- **Điều học được:** Always verify all dependencies are in place before claiming "setup complete"

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ đâu đến đâu?**
   - Input JSON (`input/EC_XXX.json`) → Data Loader (src/data_loader.py) → Policy Engine (src/policy.py) → Output Writer (src/output_writer.py) → Output JSON (`output/EC_XXX.json`)

2. **Cách xử lý 50 cases?**
   - Người 2-5 xử lý song song: Người 2-3 (Order/Seller), Người 4-5 (Payment/Delivery)
   - Intermediate results lưu vào `data/processed/person_X/`
   - Người 6 merge tất cả, apply policy, generate 50 JSON outputs

3. **Policy được apply như thế nào?**
   - Priority-based rules (1-6)
   - First match wins - không combine multiple issues
   - 6 loại issues: canceled_order_paid, unavailable_order_paid, late_delivery_seller, late_delivery_logistics, valid_split_payment, unsupported_late_claim

4. **Evidence IDs dùng để làm gì?**
   - Traceable references đến source data
   - Format: `order:<id>`, `item:<order_id>:<item_id>`, `seller:<id>`, `payment:<order_id>:<seq>`, `policy:<code>`

5. **Quality checks ở đâu?**
   - `src/validators.py`: Schema validation, evidence ID format check
   - `src/output_writer.py`: Pre-write validation
   - Policy engine: Financial calculation verification

---

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Chí Tâm
**Ngày xác nhận:** 2026-08-05
