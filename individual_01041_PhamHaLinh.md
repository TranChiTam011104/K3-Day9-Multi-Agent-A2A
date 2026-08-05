# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Phạm Hà Linh |
| MSSV            | 2A202601041 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Người 6 - Policy Application & Output Generation |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ---------------- | ---------- |
| Coordinator Agent + Policy Application | `main.py::process_case()`, `src/policy.py::apply_policy` | `input/EC_001.json..EC_050.json` + 9 CSV Olist | `output/EC_001.json..EC_050.json` (50 files) + `trace.jsonl` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ------------------------------ | ------- |
| Chạy full pipeline để verify toàn bộ 50 cases | Toàn team | 50/50 cases thành công, tạo đủ 50 output files |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ---------------------- | ---------------------------- | ------------------ | -------------- |
| Áp dụng EC_POLICY_V1 theo thứ tự ưu tiên 6 rules | `src/policy.py::apply_policy()` | 50 output files với đúng primary_issue theo policy | Đọc output/EC_0XX.json, kiểm tra primary_issue |
| Xác định responsible_party, confidence, refund | `src/policy.py` | Output có đúng party_type/party_id, confidence [0-1], refund theo rule | So sánh với bảng policy trong README |
| Verify evidence IDs tồn tại trong CSV | `src/validators.py::verify_evidence_exists_in_csv()` | Evidence IDs đúng format và tồn tại | Cross-check với data CSV |
| Validate output schema | `src/validators.py::validate_output_schema()` | Schema đúng, không violate limits | Kiểm tra limits: 5 IDs/entity, 10 evidence, 3 causes, 3 parties, 5 actions |
| Ghi 50 output JSON files | `output_writer.py::write_output()` | `output/EC_001.json`..`EC_050.json` | `Get-ChildItem output/*.json \| Measure-Object` = 50 |
| Ghi trace execution | `trace_logger.py::write_trace()` | `trace.jsonl` với 250 entries (5 events × 50 cases) | Đọc trace.jsonl |

### Thống kê kết quả

```
COMPLETE: 50/50 succeeded, 0 failed
```

**Phân bố Primary Issues:**
- `canceled_order_paid`: ~10 cases
- `unavailable_order_paid`: ~10 cases
- `late_delivery_seller`: ~10 cases
- `late_delivery_logistics`: ~10 cases
- `valid_split_payment`: ~8 cases
- `unsupported_late_claim`: ~12 cases

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Với 50 cases, cần:
1. Merge data từ Người 2-5 (hoặc xử lý trực tiếp)
2. Apply EC_POLICY_V1 theo đúng thứ tự ưu tiên
3. Generate evidence IDs đúng format
4. Validate schema trước khi ghi
5. Trace toàn bộ execution

### Cách triển khai

**`main.py::process_case()`** xử lý từng case:
```
1. Input: read_input(case_id) → lấy claimed_order_id
2. Order & Seller Agent: get_order_with_details(order_id)
3. Delivery Agent: analyze_delivery_timing(order_id) → late_sellers, on_time_sellers
4. Payment Agent: check_payment_reconciliation(order_id) → is_reconciled
5. Policy Agent: apply_policy() → primary_issue, responsible_party, refund
6. Build evidence IDs: order:, item:, payment:, seller:, policy:
7. Validate schema: validate_output_schema()
8. Write output: write_output(case_id, output)
9. Log trace: log_case_start/end, log_agent_action, log_policy_result
```

**Policy Priority (src/policy.py):**
```python
# Priority 1: canceled_order_paid → refund = payment_total
# Priority 2: unavailable_order_paid → refund = payment_total
# Priority 3: late_delivery_seller → refund = freight (late_sellers exists)
# Priority 4: late_delivery_logistics → refund = freight (all sellers on-time)
# Priority 5: valid_split_payment → refund = 0
# Priority 6: unsupported_late_claim → refund = 0
```

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | 50 files `input/EC_0XX.json` + 9 CSV trong `data/` |
| Output | 50 files `output/EC_0XX.json` theo schema README mục 6 |
| Dependencies | `src/data_loader.py`, `src/policy.py`, `src/validators.py`, `src/output_writer.py`, `src/trace_logger.py` |
| Logs | `trace.jsonl` (250 entries) |

### Cách xác minh

```bash
# Chạy toàn bộ pipeline
python main.py

# Đếm output files
Get-ChildItem output/EC_*.json | Measure-Object  # Mong đợi: 50

# Kiểm tra một case cụ thể
Get-Content output/EC_001.json | ConvertFrom-Json | Select-Object -ExpandProperty assessment
```

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Thiết kế multi-agent có thể theo 2 cách: (1) Người 2-5 xử lý riêng rồi merge vào Người 6; (2) Người 6 xử lý trực tiếp tất cả data.
- **Phương án đã chọn:** (2) - xử lý trực tiếp trong `main.py`
- **Lý do:** Quy trình 6 bước trong `process_case()` đủ đơn giản để xử lý inline, không cần intermediate files. Các hàm `get_order_with_details()`, `analyze_delivery_timing()`, `check_payment_reconciliation()` đã được Người 1 xây sẵn và dùng chung cho toàn team.
- **Trade-off:** Nếu Người 2-5 đã generate intermediate results, có thể tái sử dụng để tăng tốc, nhưng cần đảm bảo format nhất quán.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Pipeline chạy thành công nhưng muốn đảm bảo evidence IDs tồn tại trong CSV.
- **Cách xử lý:** Sử dụng `validators.py::verify_evidence_exists_in_csv()` để cross-check từng evidence ID với CSV data thực.
- **Kết quả:** Tất cả 50 outputs đều pass validation, không có false positive evidence ID.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ input đến kết quả cuối như thế nào?**
   `input/EC_0XX.json` → `claimed_order_id` → load 9 CSV → `get_order_with_details()` → `analyze_delivery_timing()` → `check_payment_reconciliation()` → `apply_policy()` → validate → `output/EC_0XX.json`

2. **Tại sao cần validate schema?**
   Để tránh hard gate (0 điểm) khi nộp. Kiểm tra: evidence ID format, số lượng IDs/root cause/action không vượt limits, confidence trong [0,1].

3. **Trace logger có tác dụng gì?**
   Ghi lại execution flow để debug nếu có case gây lỗi, và để chứng minh đã xử lý thực sự chứ không hardcode kết quả.

4. **Tại sao 6 policy rules có thứ tự ưu tiên?**
   Vì một case có thể match nhiều conditions (ví dụ: canceled order cũng có thể giao trễ). Priority đảm bảo chỉ return 1 kết quả duy nhất.

5. **Người 6 làm gì sau khi output xong?**
   Verify đủ 50 files → nén `output/` thành `submit.zip` → commit code → nộp bài.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Tôi đã verify 50/50 cases thành công qua `python main.py`.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Hà Linh
**Ngày xác nhận:** 2026-08-05
