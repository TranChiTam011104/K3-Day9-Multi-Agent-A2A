# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Hà Hoàng Tuấn Hùng   |
| MSSV            | 2A202601629       |
| Khóa/Lớp        | K3         |
| Vai trò chính   | Người 3 — ORDER & SELLER PROCESSING (EC_011 - EC_020, EC_026 - EC_030)    |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Xử lý Order & Seller (EC_011-020, 026-030) | `src/data_loader.py` (`get_order_with_details`, `analyze_delivery_timing`) | Mã `order_id` lấy từ input claim | Dict chứa thông tin `order_status`, `is_late_delivery`, `late_sellers`, `on_time_sellers` đã chuẩn hoá | Hoàn thành |
| Unit tests kiểm thử Người 3 | `tests/test_person_3.py` | Mock data CSV (pandas DataFrame cache) | 21 test cases (cover đầy đủ các scenarios vi phạm) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Sửa lỗi Parsing Datetime  | Module Data Loader chung (Người 1, 2) | Logic tính date cho toàn hệ thống không còn bị sai do so sánh chuỗi (string) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Fix lỗi so sánh string timestamp | `src/data_loader.py` | Áp dụng `pd.to_datetime()` để parse đúng thời gian giao carrier và shipping limit | `pytest tests/test_person_3.py` (pass) |
| Deduplicate danh sách Seller vi phạm | `src/data_loader.py` | Đảm bảo một `seller_id` không bị lặp lại hoặc bị dính cả vào list đúng hạn và trễ hạn khi có nhiều items | Trace dict output / tests |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Bộ 21 unit tests trong `tests/test_person_3.py` mô phỏng đủ 15 kịch bản (nhiều seller, 1 trễ 1 không, không có carrier date, v.v) đảm bảo mọi rules xác minh lỗi do seller đã được xử lý chính xác theo Policy.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

- Việc so sánh chuỗi (String) trực tiếp từ raw CSV cho các biến ngày tháng (`shipping_limit_date` vs `order_delivered_carrier_date`) gây rủi ro sai khác so sánh logic khi định dạng string thay đổi.
- Khi order có nhiều items, việc append liên tục vào mảng làm duplicate ID seller. Cùng 1 seller có thể vừa bị gắn mác "late" và "on_time" nếu item 1 trễ và item 2 đúng hạn.
- Order status chứa khoảng trắng (VD: " CANCELED ") dẫn tới việc rớt Policy matcher.

### Cách triển khai

- **Datetime Parsing**: Bọc toàn bộ các properties ngày tháng vào `pd.to_datetime(..., errors="coerce")` trước khi so sánh `>` hoặc `<`.
- **Set Deduplication**: Sử dụng `list(set(result["late_sellers"]))` để đảm bảo ID không lặp. Loại bỏ những seller đã trễ hạn ra khỏi mảng `on_time_sellers` (nếu seller đó có một item trễ, họ bị đánh trễ bất kể các items khác có kịp đi chăng nữa).
- **String Normalization**: Đặt thêm điều kiện `order["order_status"].strip().lower()` trước khi trả data ra.

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | Lịch sử order từ CSV (thông qua cache dict) |
| Output                  | Cấu trúc dictionary chứa data timing (`is_late_delivery`, `late_sellers`) |
| Module phụ thuộc        | `src.data_loader` load csv file |
| Module sử dụng output   | `src.policy.py` và `main.py` (Coordinator) |
| Điều kiện lỗi cần xử lý | Order ko có `carrier_date` -> mặc định pass (on time) |

### Cách xác minh

```bash
python -m pytest tests/
```

- **Kết quả mong đợi:** 21 tests passed (đặc biệt test `test_all_15_cases_parametrized`)
- **Kết quả thực tế:** 21 passed in 0.93s.
- **Artifact/log:** Chạy thành công.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cách thiết kế Unit test để phủ sóng nhanh 15 cases (từ EC_011 đến EC_030).
- **Các phương án đã cân nhắc:** 1) Viết 15 hàm test rời rạc tương ứng 15 JSON. 2) Dùng tính năng `pytest.mark.parametrize` kèm Data mock dictionary nội bộ.
- **Phương án đã chọn:** Phương án 2 (Dùng Parametrize).
- **Lý do:** Trade-off về cost và thời gian. Dữ liệu mock nội bộ giúp test chạy cục bộ cực nhanh, không lệ thuộc vào data file nặng bên ngoài, cấu trúc logic mạch lạc dễ quản lý và maintain hơn 15 file test riêng lẻ.
- **Bằng chứng quyết định phù hợp:** Log test chạy vỏn vẹn trong `0.93s` bao phủ mọi scenario có thể xảy ra ở Data Layer.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** KeyError: 'order_id' khi test empty dataframe của Payment Agent (Người 4, 5).
- **Lệnh hoặc bước tái hiện:** `python -m pytest tests/`
- **Nguyên nhân gốc:** Khi tạo mock `_cache["olist_order_payments_dataset.csv"] = pd.DataFrame([])`, Pandas sinh ra empty DF không có headers (columns). Khi Data Loader `data_loader.py` filter condition `payments["order_id"] == order_id`, column `order_id` không tồn tại nên raise KeyError.
- **Cách xử lý:** Bổ sung column explicitly khi init mock data: `pd.DataFrame(columns=["order_id", "payment_sequential", "payment_value"])`.
- **Cách xác minh sau khi sửa:** Chạy lại lệnh pytest, log trả về pass.
- **Điều học được:** Khi build mock data cho pandas dataframe rỗng, luôn phải define `columns=[...]` đầy đủ để các phép logic filter column nội bộ không bị crash.

## 7. Hiểu biết về luồng end-to-end

*Lưu ý: Mẫu template chứa câu hỏi về "Crossref / Vector index / Ground truth" là của lab RAG (Day 8). Thay vào đó, đây là luồng hoạt động của hệ thống E-commerce Dispute Resolution (Day 9):*

**Câu trả lời:**

1. **Coordinator Flow:** Yêu cầu (claim) ban đầu từ khách hàng dạng JSON được load vào thông qua `main.py` (Coordinator Agent). Agent này extract `claimed_order_id`.
2. **Data Agents Handoff:** Coordinator gọi các Data Agents (Order/Seller Agent, Delivery Agent, Payment Agent) tương tác với `data_loader.py`. Các Agent này tiến hành truy xuất Pandas DataFrame đã parse các file CSV liên quan, từ đó xuất ra các kết luận trung gian (có trễ hạn không? ai trễ hạn? payment có match không?).
3. **Policy Application:** Tổng hợp kết luận đưa vào Policy Agent (`policy.py`), tại đây một bộ rules có thứ tự ưu tiên (1 -> 6) sẽ được chạy, để quyết định Issue là gì (VD: `late_delivery_seller`, `canceled_order_paid`), Responsible party, và Root Cause.
4. **Validation & Resolution:** Cuối cùng, hệ thống xuất hoá đơn hoàn tiền (`recommended_refund_brl`), sinh ra các chuỗi Evidence IDs (`item:abc123:1`, `seller:XYZ`) hợp chuẩn thông qua các record có thật trong data. JSON cuối cùng được dump ra thư mục `output/` như một bản báo cáo Dispute Assessment hoàn thiện.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hà Hoàng Tuấn Hùng
**Ngày xác nhận:** 2026-08-05
