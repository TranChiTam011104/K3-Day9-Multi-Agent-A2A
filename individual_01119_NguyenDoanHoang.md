# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Nguyễn Doãn Hoàng  |
| MSSV            | 2A202601119       |
| Khóa/Lớp        | K3_E403         |
| Vai trò chính   | Người 2: Order & Seller Processing (EC_001 - EC_010, EC_021 - EC_025) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Phân tích trạng thái đơn hàng và kiểm tra thời hạn bàn giao của Seller | [person_2_agent.py](file:///d:/laragon/www/Day09Vinuni/K3-Day9-Multi-Agent-A2A/src/person_2_agent.py) | File case `input/EC_001.json` -> `input/EC_010.json` và `input/EC_021.json` -> `input/EC_025.json` + Dữ liệu Olist CSV | 15 file JSON kết quả trung gian lưu tại `data/processed/person_2/` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Hỗ trợ tích hợp và sửa lỗi kiểu dữ liệu serialize của trace logger | Toàn nhóm / [trace_logger.py](file:///d:/laragon/www/Day09Vinuni/K3-Day9-Multi-Agent-A2A/src/trace_logger.py) | Khắc phục hoàn toàn lỗi `numpy.bool_` không thể serialize được JSON, giúp ghi file `trace.jsonl` thành công cho cả 50 cases |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Xây dựng và chạy agent cho Người 2 | [person_2_agent.py](file:///d:/laragon/www/Day09Vinuni/K3-Day9-Multi-Agent-A2A/src/person_2_agent.py) | 15 file JSON trung gian lưu tại `data/processed/person_2/` | Chạy lệnh `python src/person_2_agent.py` và kiểm tra thư mục output |
| Chạy coordinator và xuất kết quả nộp bài | [submit.zip](file:///d:/laragon/www/Day09Vinuni/K3-Day9-Multi-Agent-A2A/submit.zip) và [trace.jsonl](file:///d:/laragon/www/Day09Vinuni/K3-Day9-Multi-Agent-A2A/trace.jsonl) | Gói zip chứa 50 kết quả JSON và file trace chạy thật | Chạy lệnh `python run.py` và `Compress-Archive` |

Mô tả kết quả cụ thể:
Đã hoàn thành phân tích 15 cases được giao cho Người 2. Các file trung gian lưu đúng cấu trúc và thư mục yêu cầu (`data/processed/person_2/EC_XXX_processed.json`). Toàn bộ 50 cases của hệ thống đã chạy thành công 100% không gặp lỗi, sinh ra đầy đủ 50 file JSON hợp lệ trong thư mục `output/` và đóng gói thành công file `submit.zip` để nộp bài.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong pipeline multi-agent xử lý khiếu nại của Olist, cần phân tích chi tiết dữ liệu đơn hàng và thông tin người bán (seller) để làm cơ sở xác định lỗi thuộc về ai. Cụ thể, cần xác định xem đơn hàng có bị hủy (`canceled`) hay không khả dụng (`unavailable`) không, tính tổng tiền vận chuyển (`freight_total_brl`), và xác định người bán nào bàn giao hàng cho đối tác vận chuyển muộn hơn thời hạn cam kết (`shipping_limit_date`).

### Cách triển khai
Sử dụng pandas để load các file CSV của Olist. Với mỗi case của Người 2 phụ trách:
1. Trích xuất `claimed_order_id` từ file input JSON tương ứng.
2. Truy vấn chi tiết đơn hàng từ `orders.csv` để lấy `order_status` và `order_delivered_carrier_date`.
3. Truy vấn tất cả items thuộc đơn hàng từ `order_items.csv` để lấy danh sách sản phẩm, người bán (`seller_id`), hạn bàn giao (`shipping_limit_date`), và chi phí vận chuyển (`freight_value`).
4. Duyệt qua từng item, so sánh `order_delivered_carrier_date` với `shipping_limit_date`. Nếu thời gian giao cho carrier muộn hơn hạn limit, đánh dấu item đó là giao trễ bởi seller (`is_late_handoff = True`) và thêm `seller_id` tương ứng vào danh sách người bán vi phạm (`violating_sellers`).
5. Tính tổng tiền vận chuyển bằng cách tính tổng `freight_value` của toàn bộ các items.
6. Xuất toàn bộ thông tin này thành cấu trúc JSON trung gian.

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | Đường dẫn file `input/EC_XXX.json` (chứa `claimed_order_id`) và dữ liệu thô Olist CSV. |
| Output                  | File JSON trung gian lưu tại `data/processed/person_2/EC_XXX_processed.json` chứa thông tin order_status, freight_total_brl, list seller_ids, list violating_sellers, items details và evidence_ids. |
| Module phụ thuộc        | [data_loader.py](file:///d:/laragon/www/Day09Vinuni/K3-Day9-Multi-Agent-A2A/src/data_loader.py) (nạp dữ liệu CSV). |
| Module sử dụng output   | Coordinator Agent / Policy Agent ([run.py](file:///d:/laragon/www/Day09Vinuni/K3-Day9-Multi-Agent-A2A/run.py)). |
| Điều kiện lỗi cần xử lý | Đơn hàng không tồn tại trong database (bỏ qua/ghi log cảnh báo), hoặc thiếu các mốc thời gian `order_delivered_carrier_date` / `shipping_limit_date` (phải kiểm tra hợp lệ bằng `pd.notna` để tránh lỗi so sánh). |

### Cách xác minh

```bash
python src/person_2_agent.py
```

- **Kết quả mong đợi:** 15 file JSON được ghi vào thư mục `data/processed/person_2/` từ `EC_001_processed.json` đến `EC_010_processed.json` và `EC_021_processed.json` đến `EC_025_processed.json`.
- **Kết quả thực tế:** Cả 15 file được tạo thành công, chứa đúng dữ liệu đã trích xuất từ database Olist.
- **Artifact/log:** `data/processed/person_2/EC_001_processed.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Việc so sánh các mốc thời gian (như `order_delivered_carrier_date` và `shipping_limit_date`) chứa giá trị chuỗi/ngày giờ và có thể có dữ liệu bị khuyết (`NaN`).
- **Các phương án đã cân nhắc:**
  - Phương án A: Dùng thư viện datetime chuẩn của Python để tự chuyển đổi chuỗi timestamp và so sánh.
  - Phương án B: Sử dụng Pandas (`pd.notna` và so sánh trực tiếp các chuỗi timestamp theo lexicographical order hoặc chuyển đổi sang định dạng `datetime64`).
- **Phương án đã chọn:** Phương án B (Sử dụng Pandas và `pd.notna` kiểm tra giá trị hợp lệ trước khi so sánh chuỗi timestamp).
- **Lý do:** Vì dữ liệu timestamp trong Olist CSV đồng nhất về mặt format (ISO-like string `YYYY-MM-DD HH:MM:SS`), việc so sánh trực tiếp chuỗi là chính xác và có hiệu năng cực kỳ cao mà không cần tốn chi phí parse chuỗi sang đối tượng Datetime. Đồng thời, hàm `pd.notna` của Pandas giúp lọc bỏ nhanh chóng các giá trị rỗng (`NaN`) mà không gây lỗi runtime crash.
- **Bằng chứng quyết định phù hợp:** Agent xử lý hoàn thành 15 cases cực nhanh (< 1 giây) và không gặp bất kỳ lỗi logic hay lỗi so sánh kiểu dữ liệu nào.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: Object of type bool is not JSON serializable` hoặc `TypeError: Object of type bool_ is not JSON serializable` khi chạy file `run.py`.
- **Lệnh hoặc bước tái hiện:** Chạy lệnh `python run.py`.
- **Nguyên nhân gốc:** Khi thực hiện so sánh các cột của DataFrame hoặc Series trong Pandas (ví dụ: so sánh ngày giao hàng thực tế với ngày hẹn ước), Pandas trả về kiểu dữ liệu boolean của NumPy (`numpy.bool_`) thay vì kiểu `bool` chuẩn của Python. Khi coordinator log các action của DeliveryAgent hay PaymentAgent vào trace logger, thư viện `json` mặc định của Python không hỗ trợ serialize kiểu `numpy.bool_`, dẫn đến lỗi crash hệ thống tại thời điểm ghi file `trace.jsonl`.
- **Cách xử lý:** Ép kiểu rõ ràng các giá trị boolean được trả về từ các hàm nghiệp vụ sang kiểu `bool` của Python trước khi đưa vào kết quả trả về (ví dụ: `result["is_late_delivery"] = bool(...)`).
- **Cách xác minh sau khi sửa:** Chạy lại `python run.py`, toàn bộ 50 cases chạy thành công mà không có lỗi TypeError, và file `trace.jsonl` được tạo ra hoàn toàn hợp lệ.
- **Điều học được:** Khi làm việc với thư viện Pandas/NumPy và cần xuất dữ liệu ra định dạng JSON/JSONL, luôn cần lưu ý ép kiểu các giá trị số hoặc boolean về kiểu chuẩn của Python để tránh xung đột với serializer của thư viện `json`.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Dữ liệu thô từ Crossref (metadata bài báo khoa học) được thu thập (ingested).
   - Dữ liệu được trích xuất (parsed) để lấy thông tin cần thiết: tiêu đề, tác giả, tóm tắt (abstract), ngày xuất bản, v.v.
   - Các đoạn text này được chia nhỏ (chunked) thành các segment có kích thước phù hợp (ví dụ: dùng RecursiveCharacterTextSplitter) kèm theo metadata thích hợp.
   - Sử dụng mô hình Embedding (như OpenAI text-embedding-ada-002 hoặc local model) để biến đổi các chunks này thành các vector biểu diễn ngữ nghĩa (dense vectors).
   - Các vectors cùng với metadata tương ứng được lưu trữ và lập chỉ mục (indexed) trong Vector Database (như Pinecone, Qdrant, ChromaDB, hoặc PGVector) để phục vụ cho các truy vấn tìm kiếm tương đồng (similarity search).

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - **Evaluation set (Tập đánh giá)** chứa một danh sách các câu hỏi kiểm thử (test queries) cùng với các câu trả lời tham chiếu (reference answers).
   - **Ground-truth document IDs** là danh sách các ID của những tài liệu thực sự chứa thông tin chính xác để trả lời cho từng câu hỏi tương ứng.
   - **Đo Retrieval Quality (Chất lượng tìm kiếm)**: So sánh các tài liệu được hệ thống truy xuất (retrieved documents) với ground-truth document IDs để tính toán các chỉ số như Precision@K, Recall@K, Mean Reciprocal Rank (MRR), và Normalized Discounted Cumulative Gain (NDCG).
   - **Đo Answer Quality (Chất lượng câu trả lời)**: Sử dụng các câu trả lời do LLM sinh ra kết hợp với các tài liệu được truy xuất để đánh giá qua các metrics như Faithfulness (độ trung thực của câu trả lời dựa trên tài liệu truy xuất), Answer Relevance (mức độ liên quan của câu trả lời với câu hỏi), và ROUGE/BLEU hoặc LLM-as-a-judge đối chiếu với reference answers.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (Kiểm tra chất lượng)** tập trung vào việc đánh giá tính đúng đắn, toàn vẹn của dữ liệu và hệ thống tại thời điểm kiểm thử. Ví dụ: kiểm tra định dạng schema của dữ liệu (validation), kiểm tra tính thống nhất của các phép tính tài chính (đối soát tiền khớp nhau), kiểm tra xem evidence IDs có thực sự tồn tại trong database hay không (không được bịa đặt).
   - **Freshness monitoring (Giám sát độ tươi mới)** tập trung vào yếu tố thời gian và chu kỳ cập nhật dữ liệu. Nó theo dõi xem dữ liệu trong vector index hoặc database có đang bị lỗi thời (outdated) hay không, thời gian trễ (latency) kể từ khi dữ liệu mới xuất hiện tại nguồn (Crossref) đến khi nó được lập chỉ mục xong trong vector DB là bao lâu, và có các quy trình tự động cập nhật/re-index định kỳ để đảm bảo LLM tiếp cận dữ liệu mới nhất.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Việc dùng chung một test set duy nhất đóng vai trò là "đối chứng" (controlled variables) trong phương pháp thực nghiệm khoa học.
   - Điều này giúp đảm bảo sự so sánh công bằng (fair comparison) giữa 3 phiên bản hệ thống:
     - **Baseline**: Đo hiệu năng ban đầu khi hệ thống hoạt động bình thường.
     - **Corrupted**: Đo mức độ suy giảm hiệu năng khi hệ thống bị lỗi dữ liệu hoặc cấu hình sai.
     - **Repaired**: Đo mức độ phục hồi hiệu năng sau khi đã áp dụng các bản sửa lỗi (patches/repairs).
   - Nếu sử dụng các test set khác nhau, sự thay đổi về chỉ số chất lượng (như recall, accuracy) có thể do độ khó hoặc phân phối khác nhau của câu hỏi trong test set, thay vì do sự thay đổi thực sự trong thuật toán hay chất lượng dữ liệu của hệ thống.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Artifact**:
     - Code sửa lỗi hoạt động ổn định và vượt qua toàn bộ unit/integration tests.
     - File kết quả output của test set được sinh ra đầy đủ, hợp lệ và đúng schema định dạng yêu cầu.
     - File trace log (`trace.jsonl`) ghi lại chính xác luồng xử lý không gặp lỗi.
   - **Metric**:
     - Hiệu năng hệ thống phục hồi đáng kể so với phiên bản bị hỏng (corrupted) và tiệm cận hoặc vượt qua mức baseline.
     - Chỉ số **Recall@K** hoặc **Precision@K** tăng lên mức mong đợi (ví dụ: >90%).
     - Các metrics đánh giá chất lượng câu trả lời như **Faithfulness** và **Answer Relevance** của LLM hồi phục (tỷ lệ ảo giác - hallucination rate giảm xuống gần 0%).
     - Sai số tài chính (financial reconciliation discrepancy) nằm trong biên độ sai số cho phép (ví dụ: <= 0.10 BRL) và tỷ lệ đối soát khớp đạt 100%.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Doãn Hoàng
**Ngày xác nhận:** 2026-08-05
