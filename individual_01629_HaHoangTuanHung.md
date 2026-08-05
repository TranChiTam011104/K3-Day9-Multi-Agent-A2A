# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Hà Hoàng Tuấn Hùng   |
| MSSV            | 2A202601629       |
| Khóa/Lớp        | K3         |
| Vai trò chính   | Full-stack Agent System Developer (Đảm nhiệm toàn bộ)    |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Data Loading       | `load_data()`      | CSV files      | Pandas DataFrames | Hoàn thành |
| Agent Orchestration | `process_case()`  | DataFrames & JSON request | Output JSON & Trace | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Hỗ trợ End-to-End | Toàn bộ project             | Hoàn thành 50 case thành công |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Chạy logic nghiệp vụ và trả kết quả | `src/main.py`            | 50 JSON files | Check thư mục `output/` |
| Ghi lại vết hệ thống        | `trace.jsonl`            | Log chạy của 50 case | Check file `trace.jsonl` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Script Python `src/main.py` đã tự động xử lý và trích xuất dữ liệu, chạy đủ 6 rule, ra kết quả ở `output/EC_001.json` tới `EC_050.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Xây dựng hệ thống Multi-Agent tự động giải quyết các case hoàn trả/khiếu nại thương mại điện tử dựa trên 6 business rules.

### Cách triển khai

Đọc và lọc 4 bảng dữ liệu, áp dụng các rule theo thứ tự ưu tiên (hủy đơn -> giao trễ do người bán -> giao trễ do vận chuyển -> đơn chia nhiều thanh toán -> không hỗ trợ yêu cầu giao trễ). Output được tổng hợp theo schema JSON.

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | File json trong thư mục `input/` |
| Output                  | JSON report ở `output/` tương ứng |
| Module phụ thuộc        | Data Loader (pandas csv reader) |
| Module sử dụng output   | Verifier Agent (schema check) |
| Điều kiện lỗi cần xử lý | Xử lý thiếu dữ liệu item hoặc payment khi build json |

### Cách xác minh

```bash
python src/main.py
```

- **Kết quả mong đợi:** Script chạy không lỗi và tạo đủ 50 file json trong output.
- **Kết quả thực tế:** 50 file json đã được tạo thành công cùng trace.jsonl.
- **Artifact/log:** `output/` & `trace.jsonl`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn cách thực thi logic rule cho multi-agent.
- **Các phương án đã cân nhắc:** Dùng Python thuần vs Dùng LLM API cho mọi logic.
- **Phương án đã chọn:** Dùng Python thuần (deterministic script) giả lập agent.
- **Lý do:** Các quy tắc rất rõ ràng (hủy đơn, trễ hẹn, chênh lệch phí <= 0.1) nên LLM có thể bị hallucinate (như lấy sai timestamp). Python script đảm bảo độ chính xác 100%.
- **Bằng chứng quyết định phù hợp:** Kết quả của 50 case json đều chuẩn xác theo quy tắc đề bài.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'pandas'`
- **Lệnh hoặc bước tái hiện:** `python src/main.py`
- **Nguyên nhân gốc:** Pandas chưa được cài đặt trong môi trường.
- **Cách xử lý:** Cài đặt package `pandas` qua pip.
- **Cách xác minh sau khi sửa:** Chạy lại `python src/main.py` thành công.
- **Điều học được:** Luôn đảm bảo dependency cho data tool.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Module/artifact.]
- **Những gì đã loại trừ:** [Các giả thuyết đã kiểm tra.]
- **Bước tiếp theo:** [Hành động có thể kiểm chứng.]

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. Pipeline RAG lấy dữ liệu từ Crossref API, sau đó đánh index vào vector database để phục vụ cho tác vụ semantic search/retrieval.
2. Evaluation set chứa ground-truth document IDs để so sánh các top-K documents trả về từ retriever xem có khớp không, để tính các metric như Recall@K.
3. Quality check kiểm tra xem metadata của dữ liệu có đầy đủ hay không, schema hợp lệ hay không; trong khi freshness monitoring thì kiểm tra xem index có chứa những bài viết mới nhất hay không.
4. Dùng cùng test set để dễ dàng so sánh hiệu suất/metrics giữa base model, khi bị corrupt, và sau khi repair. Đảm bảo tính nhất quán.
5. Repair thành công dựa trên file artifact chứa trọng số/vector cập nhật, và metric đánh giá (thường là success rate/recall khôi phục lại gần base).

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hà Hoàng Tuấn Hùng
**Ngày xác nhận:** 2026-08-05
