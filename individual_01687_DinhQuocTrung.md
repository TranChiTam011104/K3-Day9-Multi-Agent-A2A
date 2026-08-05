# Báo cáo vai trò cá nhân — Day 9: Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                              |
| --------------- | ------------------------------------- |
| Họ và tên       | Đinh Quốc Trung                       |
| MSSV            | 2A202601687                           |
| Khóa/Lớp        | K3                                    |
| Vai trò chính   | Người 5 — Payment & Delivery Analysis |
| Ngày hoàn thành | 2026-08-05                            |

## 2. Vai trò và phạm vi công việc

Tôi sở hữu bước phân tích payment/delivery cho đúng 10 case `EC_041`–`EC_050`. Đầu vào là các file case trong `input/` và dữ liệu có thể kiểm chứng từ Olist. Đầu ra bàn giao cho Người 6 là 10 JSON trung gian trong `data/processed/person_5/`.

| Module/deliverable   | File/hàm phụ trách                                  | Input                                                                         | Output                                         | Trạng thái |
| -------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------- | ---------- |
| Processor Người 5    | `src/person_5_processor.py`                         | `input/EC_041.json`–`EC_050.json`, orders, order items, payments, sellers CSV | Facts payment, delivery, financial và evidence | Hoàn thành |
| Intermediate handoff | `data/processed/person_5/EC_041.json`–`EC_050.json` | Kết quả processor                                                             | 10 JSON cho coordinator                        | Hoàn thành |
| Kiểm thử             | `tests/test_person_5_processor.py`                  | Processor và CSV thật                                                         | 20 test                                        | Hoàn thành |

Tôi không áp dụng policy để chọn `primary_issue`, không tạo file trong `output/`, không sinh `submit.zip` và không nhận ownership phần của Người 2, 3, 4 hoặc 6.

## 3. Kết quả bàn giao

- Đọc tổng payment và giữ từng payment row theo `payment_sequential`.
- Đánh dấu split payment khi có ít nhất hai payment rows. Trong 10 case, `EC_046` có hai rows: 39.17 BRL và 86.84 BRL, tổng 126.01 BRL.
- Tính `item_total_brl`, `freight_total_brl`, `expected_total_brl`, `payment_total_brl`, độ lệch và đối soát với tolerance 0.10 BRL.
- So sánh `order_delivered_customer_date` với `order_estimated_delivery_date` và so sánh carrier handoff với `shipping_limit_date` trên từng item.
- Giữ giá trị thiếu dưới dạng JSON `null`; không biến order chưa giao thành “giao đúng hạn”.
- Tạo evidence IDs từ các dòng có thật trong CSV và kiểm tra lại sự tồn tại trước khi ghi artifact.

Kết quả quan sát trực tiếp từ 10 artifact: `EC_041` và `EC_045` có trạng thái `canceled`; `EC_046` là split payment; `EC_043`, `EC_044`, `EC_049`, `EC_050` được giao sau estimated date. Trong đó seller handoff trễ ở `EC_043`, `EC_044`, còn handoff đúng hạn ở `EC_049`, `EC_050`. Cả 10 case có payment đối soát được với độ lệch 0.0 BRL.

## 4. Giải thích kỹ thuật

Processor giới hạn cứng case ID bằng `PERSON_5_CASE_IDS`. Mỗi case được kiểm tra `case_id`, `policy_version` và `claimed_order_id` trước khi join dữ liệu. Tổng tiền được tính trực tiếp từ từng dòng `price`, `freight_value` và `payment_value`, sau đó làm tròn hai chữ số. Mốc thời gian được parse bằng `pandas.to_datetime`; phép so sánh trả về `null` nếu thiếu một trong hai mốc.

Handoff JSON chứa:

- định danh case/order, policy version và danh sách source tables;
- trạng thái order;
- payment count, split flag, payment rows và payment total;
- ba timestamp giao hàng, cờ giao sau estimate và handoff theo từng item/seller;
- item/freight/expected/payment totals, difference, tolerance và reconciliation flag;
- evidence IDs cho order, item, payment và seller.

Việc chọn primary issue, responsible party, refund và action được để cho policy/coordinator agent, đúng ranh giới phân công.

## 5. Cách xác minh

Các lệnh đã chạy tại root repository:

```bash
python -m pytest -q tests/test_person_5_processor.py
python -m compileall -q src tests
python -m src.person_5_processor
python -m pytest -q
```

Kết quả thực tế:

- Test chuyên biệt và toàn bộ test suite: `20 passed`.
- Compile check: thành công, exit code 0.
- Processor: ghi 10 file vào `data/processed/person_5/`.
- Lượt kiểm tra artifact độc lập: `VALIDATED_FILES=10`; không có `NaN`, đủ đúng `EC_041`–`EC_050`, mọi evidence ID tồn tại trong CSV, mọi phép cộng và difference khớp.

## 6. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** canceled order không có `order_delivered_customer_date`.
- **Phương án cân nhắc:** gán `False` cho “delivered after estimate”, hoặc giữ trạng thái chưa xác định.
- **Phương án chọn:** ghi `delivered_after_estimate: null` khi thiếu timestamp.
- **Lý do:** `False` có thể bị coordinator hiểu sai thành bằng chứng giao đúng hạn. `null` phản ánh đúng dữ liệu nguồn và policy ưu tiên vẫn có thể xử lý canceled order dựa trên status/payment.
- **Bằng chứng:** `EC_041` và `EC_045` có timestamp giao khách bị thiếu; test `test_canceled_case_preserves_missing_delivery_as_null` đã pass.

## 7. Lỗi đã xử lý

- **Triệu chứng:** test split payment đầu tiên kỳ vọng sai hai giá trị 100.0 và 26.01 BRL cho `EC_046`.
- **Nguyên nhân gốc:** suy đoán cách chia tổng payment thay vì kiểm tra từng dòng CSV.
- **Cách xử lý:** đối chiếu `olist_order_payments_dataset.csv` và sửa expectation thành 39.17 và 86.84 BRL.
- **Xác minh:** chạy lại `python -m pytest -q`; 20 test pass.
- **Bài học:** tổng tiền đúng không chứng minh từng payment row đúng; handoff cần giữ row-level evidence và test phải bám dữ liệu nguồn.

## 8. Hiểu biết luồng end-to-end

Coordinator đọc `claimed_order_id` từ input và giao phần tra cứu theo domain. Các processor join order với items, sellers và payments bằng khóa trong README, rồi bàn giao facts cùng evidence IDs. Payment/delivery handoff của Người 5 chỉ chứa dữ liệu đã đối soát. Policy agent áp `EC_POLICY_V1` theo thứ tự ưu tiên để chọn issue, responsible party, refund và action. Verifier kiểm tra schema, giới hạn tập thực thể, số tiền và sự tồn tại của evidence trước khi writer tạo 50 output cuối. Trace của lượt chạy cuối và metadata được giữ ngoài file nộp; `submit.zip` chỉ được chứa 50 JSON trong `output/`.

## 9. Cam kết

- [x] Báo cáo phản ánh đúng phần việc trực tiếp thực hiện.
- [x] Có thể giải thích luồng end-to-end và ranh giới handoff.
- [x] Không ghi thành công cho bước chưa kiểm chứng.
- [x] Không chứa `.env`, API key, token hoặc secret.
- [x] Không nhận ownership phần việc của thành viên khác.

**Họ và tên:** Đinh Quốc Trung  
**Ngày xác nhận:** 2026-08-05
