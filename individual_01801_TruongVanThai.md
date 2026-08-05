# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Trương Văn Thái |
| MSSV            | 2A202601801 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Person 4 — Payment & Delivery Analysis (EC_031–EC_040) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ---------------- | ---------- |
| Payment & Delivery Analysis cho 10 case EC_031–EC_040 | `src/person_4_agent.py`, dùng `src/data_loader.py::check_payment_reconciliation`, `analyze_delivery_timing` | `input/EC_031.json`..`EC_040.json` + 9 CSV Olist qua `data_loader.py` | `data/processed/person_4/EC_031_processed.json`..`EC_040_processed.json` | Hoàn thành |

Chỉ nhận ownership cho đúng 10 case trong danh sách được phân công ở `PHANCONG.md` (Người 4), không đụng vào case của Người 2/3/5.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ------------------------------ | ------- |
| Phát hiện repo team chưa có `.gitignore` ở root (không có gì chặn `.env`/API key bị commit nhầm) | Toàn team | Đã báo lại nhóm, chưa merge vào `main` — cần một PR riêng để không lẫn với phần việc Person 4 |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ---------------------- | ---------------------------- | ------------------ | -------------- |
| Tính tổng payment, kiểm tra split payment (≥2 dòng), đối soát payment với item+freight trong sai số 0.10 BRL | `src/person_4_agent.py` → `check_payment_reconciliation()` | 10 file `*_processed.json` có `payments`, `payment_total_brl`, `difference_brl`, `is_reconciled` | `python src/person_4_agent.py` |
| So sánh `order_delivered_customer_date` với `order_estimated_delivery_date`; xác định seller nào bàn giao trễ hạn `shipping_limit_date` | `src/person_4_agent.py` → `analyze_delivery_timing()` | Field `is_late_delivery`, `late_sellers`, `on_time_sellers` trong 10 file trên | Đọc thủ công từng file trong `data/processed/person_4/` |

Output cụ thể: `data/processed/person_4/EC_031_processed.json` — `item_total_brl=82.0` + `freight_total_brl=7.44` = `89.44` = `payment_total_brl`, `difference_brl=0.0`, `is_reconciled=true`; `is_late_delivery=true` nhưng seller `88ae906ea2acf6971f26c3e8b7cb4357` nằm trong `on_time_sellers` (không có `late_sellers`) — đúng theo README mục 4, case này sẽ được Người 6 map thành `late_delivery_logistics` (lỗi do carrier, không phải seller) khi áp policy.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Với 10 case EC_031–EC_040, cần trả lời 2 câu hỏi nghiệp vụ mà `EC_POLICY_V1` cần để xếp loại: (1) payment có khớp với item + freight trong sai số 0.10 BRL không, có phải split payment hợp lệ không (≥2 dòng payment); (2) đơn có giao trễ so với `order_estimated_delivery_date` không, và nếu trễ thì do seller bàn giao muộn (`order_delivered_carrier_date > shipping_limit_date`) hay do logistics/carrier giao muộn dù seller đã bàn giao đúng hạn.

### Cách triển khai

`src/person_4_agent.py` lặp qua danh sách 10 `case_id` cố định (`EC_031`..`EC_040`), với mỗi case: đọc `input/EC_0XX.json` qua `read_input()`, lấy `claimed_order_id` qua `get_case_order_id()`, gọi `get_order_with_details()` để lấy payment rows thô (cần `payment_sequential` thật cho evidence ID), rồi gọi hai hàm dùng chung do Người 1 xây trong `data_loader.py`: `check_payment_reconciliation()` (tính `item_total_brl`/`freight_total_brl`/`payment_total_brl`, so sánh sai số 0.10 BRL) và `analyze_delivery_timing()` (parse timestamp, so `order_delivered_customer_date` với `order_estimated_delivery_date`, và với từng item xác định seller có bàn giao trễ hạn hay không). Không viết lại logic riêng để tránh lệch kết quả với Người 5 (xử lý cùng loại nhiệm vụ trên EC_041–EC_050). Kết quả trung gian — gồm cả `evidence_ids` dạng `order:<id>` và `payment:<id>:<seq>` — được ghi ra `data/processed/person_4/<case_id>_processed.json` để Người 6 gộp vào `apply_policy()`.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | 10 file `input/EC_031.json`..`EC_040.json` + 9 CSV trong `data/` (qua cache của `data_loader.py`) |
| Output | `data/processed/person_4/EC_0{31..40}_processed.json` — JSON gồm order_status, delivery timing, payment rows, các cờ `is_reconciled`/`is_late_delivery`, `evidence_ids` |
| Module phụ thuộc | `src/data_loader.py` (`get_order_with_details`, `check_payment_reconciliation`, `analyze_delivery_timing`), `src/output_writer.py` (`read_input`, `get_case_order_id`) |
| Module sử dụng output | Người 6 — `src/policy.py::apply_policy` + tổng hợp `output/EC_0XX.json` cuối cùng |
| Điều kiện lỗi cần xử lý | `order_id` không tồn tại trong `orders.csv` → `get_order_with_details` trả `{"error": ...}`; script in cảnh báo và bỏ qua case đó thay vì crash toàn bộ batch |

### Cách xác minh

```bash
python -m pip install -r requirements.txt
python src/person_4_agent.py
```

- **Kết quả mong đợi:** đủ 10 file `EC_031_processed.json`..`EC_040_processed.json` trong `data/processed/person_4/`, mỗi file có `item_total_brl + freight_total_brl ≈ payment_total_brl` (sai số ≤0.10 BRL) khi `is_reconciled=true`.
- **Kết quả thực tế:** chạy thành công, tạo đủ 10 file, không case nào bị lỗi `order not found`. Kiểm tra tay case `EC_031`: `82.0 + 7.44 = 89.44 = payment_total_brl`, `difference_brl = 0.0`.
- **Artifact/log:** `data/processed/person_4/EC_031_processed.json` .. `EC_040_processed.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Có thể tự viết logic đối soát payment + so sánh ngày giao hàng riêng trong `person_4_agent.py`, hoặc dùng lại hai hàm `check_payment_reconciliation()`/`analyze_delivery_timing()` mà Người 1 đã có sẵn trong `data_loader.py`.
- **Các phương án đã cân nhắc:** (1) Viết hàm riêng để chủ động kiểm soát toàn bộ logic; (2) Tái sử dụng hàm dùng chung của Người 1.
- **Phương án đã chọn:** (2) — tái sử dụng hàm dùng chung.
- **Lý do:** Nếu Người 4 và Người 5 (cùng làm nhiệm vụ Payment/Delivery trên 2 nhóm case khác nhau) tự viết lại cách parse timestamp và so sánh `shipping_limit_date`, rất dễ lệch nhau ở edge case (giá trị thiếu/NaT), khiến Người 6 nhận về hai bộ số liệu không nhất quán dù cùng một định nghĩa nghiệp vụ. Dùng chung hàm đảm bảo toàn bộ 20 case Payment/Delivery được tính theo đúng một logic duy nhất, giảm rủi ro mất điểm ở tiêu chí Financial resolution (20% điểm) do sai lệch giữa các case do người khác nhau xử lý.
- **Bằng chứng quyết định phù hợp:** `check_payment_reconciliation()` áp đúng sai số 0.10 BRL theo README mục 4; đối chiếu tay trên `EC_031` khớp 100% (`82.0 + 7.44 = 89.44`).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi đọc `src/policy.py` để hiểu `apply_policy()` trước khi viết `person_4_agent.py`, nội dung đọc được không khớp bản team đã commit trên `origin/main` — thấy tên hàm/biến lạ (`_ROOT_CAUSE_BY_ISSUE`...) thay vì `class PrimaryIssue(Enum)` như bản team.
- **Lệnh hoặc bước tái hiện:** `git branch --show-current` → trả về `thai-test` thay vì nhánh đang cần (`main`/`thai`).
- **Nguyên nhân gốc:** Trước đó đã `git checkout main` để pull code team, nhưng do thao tác song song (VS Code + terminal trên cùng repo), nhánh local bị chuyển ngược về `thai-test` — một nhánh cá nhân cũ chứa bản thử nghiệm khác — nên đang đọc nhầm `src/policy.py` phiên bản cũ của mình, không phải bản team.
- **Cách xử lý:** Chạy `git status` + `git log --oneline -3` để xác nhận lại branch hiện tại và commit gốc; sau đó `git checkout thai` (nhánh cá nhân đúng convention team đặt theo tên, giống `hoangne`/`hung`) rồi `git merge main --ff-only` để đưa nhánh lên ngang `origin/main` mới nhất trước khi viết code mới.
- **Cách xác minh sau khi sửa:** Đọc lại `src/policy.py`, xác nhận đúng `class PrimaryIssue(Enum)` / `check_canceled_order_paid()` như bản team đã commit qua PR #1, #2.
- **Điều học được:** Luôn `git branch --show-current` để xác nhận đúng nhánh trước khi đọc/sửa code dùng chung, nhất là khi có nhiều công cụ (VS Code Git panel + terminal) cùng thao tác trên một repo.

## 7. Hiểu biết về luồng end-to-end

> 5 câu hỏi gốc trong template này nhắc tới "Crossref"/"vector index" — có vẻ là nội dung sao chép sót từ một bài lab RAG khác, không khớp bài lab e-commerce dispute resolution này. Dưới đây trả lời theo đúng tinh thần từng câu, áp vào hệ thống thực tế của nhóm.

**Câu trả lời:**

1. **Dữ liệu đi từ input đến kết quả cuối như thế nào?** `input/EC_0XX.json` chứa `claimed_order_id` → `data_loader.py` load 9 CSV Olist, tra cứu order/items/payments/sellers theo `order_id` → Người 2/3 (Order & Seller) và Người 4/5 (Payment & Delivery) phân tích domain riêng trên 4 nhóm case, ghi kết quả trung gian vào `data/processed/person_X/` → Người 6 gộp lại, gọi `apply_policy()` theo đúng thứ tự ưu tiên 6 rule của `EC_POLICY_V1`, dựng `evidence_ids`/`affected_entities`, validate qua `validators.py`, rồi ghi `output/EC_0XX.json`.
2. **"Evaluation set" và ground-truth dùng để đo ra sao?** 50 case chính thức (EC_001–EC_050) là tập cố định duy nhất, không có nhãn đúng/sai công khai để nhóm tự so sánh nội bộ — "đúng" được kiểm tra gián tiếp qua `validators.py` (evidence ID có tồn tại thật trong CSV không, số lượng ID/root cause/action có vượt giới hạn không) và cuối cùng qua hệ thống chấm điểm của đề bài trên 6 tiêu chí có trọng số.
3. **Quality check khác gì so với "chạy không lỗi"?** `validators.py::verify_evidence_exists_in_csv` kiểm tra từng evidence ID có thật trong CSV (không chỉ đúng regex), `validate_financial_totals` kiểm tra sai số 0.10 BRL, `validate_output_schema` kiểm tra giới hạn số lượng ID/root cause/action — đây là lớp kiểm tra độc lập với logic `policy.py`, dùng để bắt case sẽ bị hard-gate 0 điểm trước khi nộp, chứ không chỉ dựa vào việc script chạy xong không crash.
4. **Vì sao Người 4 và Người 5 phải dùng chung `check_payment_reconciliation`/`analyze_delivery_timing`?** Nếu mỗi người tự viết lại, hai nhóm case (EC_031–040 và EC_041–050) có thể bị tính sai số hoặc "trễ giao hàng" theo hai định nghĩa hơi khác nhau ở edge case, khiến Người 6 áp policy không nhất quán giữa hai nhóm case dù cùng một loại nghiệp vụ Payment/Delivery.
5. **Phần việc Người 4 được coi là hoàn tất dựa trên artifact/metric nào?** Đủ 10 file `data/processed/person_4/EC_0{31..40}_processed.json`, mỗi file có `is_reconciled`/`is_late_delivery` tính từ dữ liệu thật (không suy diễn sự kiện không có trong CSV, đúng lưu ý ở README mục 2); và khi Người 6 build output cuối, các evidence_ids `order:`/`payment:` trong đó phải khớp 100% với ID đã thu thập ở bước này khi chạy qua `validators.py::verify_evidence_exists_in_csv`.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trương Văn Thái
**Ngày xác nhận:** 2026-08-05
