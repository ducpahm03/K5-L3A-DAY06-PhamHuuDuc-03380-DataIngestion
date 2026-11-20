# Báo cáo cá nhân — Day 6: Data Ingestion Engineering

- Họ và tên: Phạm Hữu Đức
- MSSV: 2A202603383
- Lớp: L3A

---

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - **Chủ đề:** Giáo trình công nghệ và kỹ năng số nơi làm việc (*Workplace Software and Skills* - Chapter 1: *Technology in Everyday Life and Business*).
  - **Nguồn & Bản quyền:** OpenStax, Rice University. Bản quyền mở quốc tế **Creative Commons Attribution 4.0 International (CC BY 4.0)**, hoàn toàn hợp lệ để sử dụng trong nghiên cứu và học thuật.
  - **Quy tắc tính trang:** File PDF trích xuất gồm 51 trang vật lý (tương ứng từ trang 16 đến 66 của bản gốc 1.047 trang). Sau khi loại trừ trang bìa chương (trang 1) và 2 trang bài tập trắc nghiệm cuối chương (trang 50–51), tổng số trang nội dung học thuật hữu ích là **48 trang** (đạt và vượt xa mốc tối thiểu 30 trang theo yêu cầu đề bài).
- **Chuẩn hóa, lỗi và giới hạn:**
  - Chuẩn hóa Unicode NFC (`unicodedata.normalize('NFC', text)`).
  - Tự động sửa lỗi ngắt dòng gạch nối của file PDF (ví dụ `read-\nonly` $\rightarrow$ `read-only`, `hard-\nwired` $\rightarrow$ `hardwired`).
  - Gộp khoảng trắng thừa và chuẩn hóa phân đoạn đoạn văn `\n\n`.
  - Giới hạn: Bảng biểu phức tạp và chú thích hình ảnh (figure caption) đôi khi bị trích xuất đan xen vào giữa dòng văn bản chính.
- **Embedding model, vector store, metric, lệnh chạy và chi phí:**
  - **Embedding model:** Google `gemini-embedding-001` (3072 chiều vector).
  - **Vector store:** Qdrant local persistent mode (`qdrant-client` v1.20.0), lưu trữ cục bộ tại `starter/qdrant_db/`, metric: Cosine Similarity.
  - **Lệnh chạy tái lập:** `cd starter; .\.venv\Scripts\python.exe -m src.run`
  - **Chi phí:** 0 VNĐ (sử dụng gói Free Tier của Gemini API và Qdrant local).
- **Metadata bắt buộc & trường lọc bổ sung:**
  - Bắt buộc: `document_id` (`openstax-workplace-skills-ch01`), `source` (`data/chapter1_workplace_skills.pdf`), `page` (1–51).
  - Trường lọc bổ sung: `section` (`1.1_history`, `1.2_hardware_network`, `1.3_cloud_iot`, `1.4_security_ethics`, `1.5_review`) và `chapter` (1).
  - Lý do chọn: Cho phép người dùng hoặc AI Agent giới hạn phạm vi truy xuất đúng mục tiêu kiến thức (ví dụ: chỉ tìm trong phần Mạng máy tính hoặc chỉ tìm trong phần Bảo mật).

---

## Cấu hình và benchmark
- **A / B / C (Tham số cụ thể, khác biệt duy nhất B–C):**
  - **Cấu hình A (Fixed-size):** Cắt cửa sổ cố định kích thước 500 ký tự, bước nhảy overlap 50 ký tự. Truy xuất Top-3 Cosine similarity thuần túy, không filter. Sinh ra **373 chunks**.
  - **Cấu hình B (Structure-aware):** Cắt theo ranh giới đoạn văn (`\n\n`), tối đa 800 ký tự/chunk. Nếu đoạn văn vượt quá 800 ký tự mới cắt chia nhỏ. Truy xuất Top-3 Cosine similarity thuần túy, không filter. Sinh ra **244 chunks**.
  - **Cấu hình C (B + Metadata Filter):** Sử dụng chung 100% chunks và vector của Cấu hình B. Điểm khác biệt duy nhất: Khi câu hỏi có chỉ định trường `filter` (ví dụ `{"section": "1.2_hardware_network"}`), hệ thống sẽ áp dụng bộ lọc cứng (`Filter.must`) trong Qdrant trước khi xếp hạng Cosine similarity.
- **≥20 câu benchmark (15 dev / 5 test):**
  - Đã xây dựng và cố định 20 câu hỏi trong `benchmark/questions.json` trước khi chạy thực nghiệm.
  - Phân chia: 15 câu `dev` (q01–q15) và 5 câu `test` holdout (q16–q20).
  - Có 5 câu có metadata filter (3 câu ở tập dev: q06, q07, q11; 2 câu ở tập test: q17, q19).
  - Toàn bộ bằng chứng (`evidence_quote`) được kiểm chứng khớp nguyên văn 100% với nội dung trang nguồn sau chuẩn hóa.
- **Tiêu chí chọn chiến lược chốt trước khi xem test:**
  - Tiêu chí 1: Evidence Hit@3 phải đạt tối thiểu 90% trên tập dev.
  - Tiêu chí 2: Tính mạch lạc (Chunk Coherence) phải đạt $\ge 1.5/2.0$ để LLM đọc hiểu trọn vẹn ngữ cảnh.
  - Tiêu chí 3: Tối ưu tài nguyên lưu trữ (số lượng chunks ít hơn).

---

## Kết quả

### Bảng 1: Hiệu năng truy xuất và tài nguyên
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| **A (Fixed 500)** | Dev | 13/15 (86.67%) | 15/15 (100.0%) | 373 | 1.78s | 0$ |
| | Test | 5/5 (100.0%) | 5/5 (100.0%) | 373 | - | 0$ |
| | **All** | **18/20 (90.0%)** | **20/20 (100.0%)** | **373** | **1.78s** | **0$** |
| **B (Paragraph 800)** | Dev | 11/15 (73.33%) | 15/15 (100.0%) | 244 | 122.88s* | 0$ |
| | Test | 5/5 (100.0%) | 5/5 (100.0%) | 244 | - | 0$ |
| | **All** | **16/20 (80.0%)** | **20/20 (100.0%)** | **244** | **122.88s** | **0$** |
| **C (Para + Filter)** | Dev | 11/15 (73.33%) | 15/15 (100.0%) | 244 | 0.10s** | 0$ |
| | Test | 5/5 (100.0%) | 5/5 (100.0%) | 244 | - | 0$ |
| | **All** | **16/20 (80.0%)** | **20/20 (100.0%)** | **244** | **0.10s** | **0$** |

*\* Thời gian bao gồm cả độ trễ chờ giải tỏa quota (cooldown) API của Gemini Free Tier khi embedding lần đầu.*
*\*\* Cấu hình C tái sử dụng vector store của B, chỉ đo thời gian truy xuất có filter.*

---

### Bảng 2: Đánh giá chất lượng ngôn ngữ và độ tin cậy
| Strategy | Coherence trung bình /2 (n=10) | Metadata đủ và đúng (n/N, n=15) | Filter tuân thủ (n/N) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| **A** | 1.0 / 2.0 (10 vị trí) | 15/15 (100.0%) | 3/5 (60.0%) | Mức 2: 5 câu (Trung bình: 2.0 / 2.0) |
| **B** | 2.0 / 2.0 (10 vị trí) | 15/15 (100.0%) | 2/5 (40.0%) | Mức 2: 5 câu (Trung bình: 2.0 / 2.0) |
| **C** | 2.0 / 2.0 (10 vị trí) | 15/15 (100.0%) | **5/5 (100.0%)** | Mức 2: 5 câu (Trung bình: 2.0 / 2.0) |

- **Đường dẫn trace và nhãn:**
  - Toàn bộ trace chi tiết 20 câu hỏi lưu tại: `results/traces.json`.
  - Bảng tổng hợp số liệu lưu tại: `results/summary.json`.
  - Mẫu chọn chấm Coherence: 10 vị trí nguồn tại các trang 3, 4, 8, 12, 16, 24, 28, 34, 41, 44.
  - Mẫu chọn chấm Grounding: 5 câu hỏi tập Test độc lập (q16, q17, q18, q19, q20).

---

## Phân tích và kết luận

### 1. So sánh đối chứng A–B và B–C:
- **So sánh A vs B (Ảnh hưởng của chiến lược chia Chunk):**
  - *Tài nguyên:* Cấu hình B giảm từ **373 xuống 244 chunks** (tiết kiệm **34.6%** dung lượng lưu trữ vector và số lượt gọi embedding).
  - *Retrieval:* Hit@3 cả hai cấu hình đều đạt tuyệt đối **100% (20/20)**. Cấu hình A đạt Hit@1 cao hơn B (90% vs 80%) do kích thước chunk nhỏ (500 ký tự) làm cô đọng mật độ từ khóa.
  - *Độ mạch lạc (Coherence):* Cấu hình B vượt trội hoàn toàn (2.0/2.0 so với 1.0/2.0 của A). Ở cấu hình A, việc cắt cứng 500 ký tự làm câu văn liên tục bị đứt ngang giữa ý (ví dụ cắt cụt giữa câu giải thích Hollerith patent ở trang 3 và giữa câu định nghĩa ROM ở trang 24).
- **So sánh B vs C (Ảnh hưởng của Metadata Filter):**
  - Cấu hình C đạt tỷ lệ tuân thủ filter tuyệt đối **100% (5/5)**, trong khi B chỉ đạt 40% (2/5).
  - Khi không có filter, câu hỏi về thiết bị mạng (q16, q17) dễ bị kéo các đoạn từ phần lịch sử (1.1) hoặc review (1.5) lên top-3 do có chung từ khóa `device` hoặc `computer`. Cấu hình C chặn đứng hoàn toàn hiện tượng này.

### 2. Hai ví dụ sai lệch điển hình:
1. **Câu q03 (Dev) - Chiến lược B:**
   - *Câu hỏi:* "How have nontechnical industries like agriculture adopted computing technology?"
   - *Gold page:* Trang 8 (`evidence_quote`: *"for example, farmers can control irrigation and monitor field conditions"*).
   - *Hiện tượng:* Ở Chiến lược B, chunk trúng evidence chỉ xếp hạng Top-2 (Hit@1 = False). Top-1 lại là một đoạn ở trang 7 nói chung về công nghệ trong kinh doanh vì chứa nhiều từ khóa lặp lại (`technology`, `industries`).
2. **Câu q17 (Test) - Chiến lược B (khi không dùng filter):**
   - *Câu hỏi:* "What allows users to save information outside of the computer unit for portable use?" (Filter chỉ định: `1.2_hardware_network`).
   - *Hiện tượng ở B:* Mặc dù top-1 tìm đúng đoạn ổ đĩa di động ở trang 24, nhưng ở vị trí Top-3 lại xuất hiện chunk từ trang 38 (Section 1.3 về Cloud Storage) vì cả 2 đều nói về việc lưu trữ tài liệu bên ngoài máy tính. Khi bật filter ở **Chiến lược C**, Top-3 được làm sạch 100% chỉ nằm trong Section 1.2.

### 3. Chiến lược lựa chọn và đánh đổi:
- **Chiến lược được chọn: Cấu hình C (Paragraph Chunking + Metadata Filter).**
- *Lý do:* Đạt điểm Coherence tuyệt đối (2.0/2.0), Hit@3 đạt 100%, bảo vệ chặt chẽ ngữ cảnh truy xuất nhờ Metadata Filter và tiết kiệm 34.6% tài nguyên so với fixed-size.
- *Đánh đổi:* Hit@1 thấp hơn A khoảng 10% (do chunk dài 800 ký tự chứa nhiều ngữ cảnh xung quanh nên điểm cosine similarity phân tán hơn so với chunk ngắn 500 ký tự). Tuy nhiên trong hệ thống RAG thực tế, LLM nhận Top-3 chunks nên Hit@3 đạt 100% là yếu tố quyết định.

### 4. Hạn chế và hướng mở rộng:
- *Hạn chế:* Dữ liệu chỉ gồm 1 chương giáo trình (51 trang); tập test gồm 5 câu là mẫu kiểm tra nhỏ.
- *Hướng cải tiến:* Áp dụng thêm **Hybrid Search (Dense Cosine + Sparse BM25)** kết hợp **Reranker** (Cohere hoặc BGE-Reranker) để đẩy chunk chứa bằng chứng chính xác từ Top-3 lên Top-1.
