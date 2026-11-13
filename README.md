# Day 06 · Data Ingestion Engineering — Bài nộp cá nhân

Biến tài liệu thành kho tri thức truy xuất được cho AI agent và benchmark chiến lược chuẩn bị dữ liệu. *(Đề bài gốc: `GUIDE.md`, `BENCHMARK.md`, `RUBRIC.md`; báo cáo: `report/individual/2A202603384_HoangBaoNguyen.md`.)*

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| 116 trang nội dung (2 báo cáo World Bank, CC BY-NC 3.0 IGO) | 3 cấu hình A/B/C, mỗi cặp đổi đúng 1 yếu tố | 20 câu (15 dev / 5 test), 4 câu filter |

## Kết quả chính (số tử/mẫu, chi tiết `results/metrics.json`)

| Strategy | Chunking | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 | Coherence /2 | Grounding test /2 |
|---|---|---|---|---|---|---|---|
| A | cố định 500/50 | 6/15 | 7/15 | 2/5 | 3/5 | 1,21 | 1,60 |
| B | theo đoạn + heading (≤1000) | 6/15 | **11/15** | 1/5 | 1/5 | **1,59** | 1,20 |
| C | = B + filter `report` | **7/15** | **11/15** | 1/5 | 1/5 | **1,59** | 1,00 |

**Chọn C** theo tiêu chí chốt trước khi xem test (dev Hit@3 → dev Hit@1 → grounding → tài nguyên); filter tuân thủ 3/3 trên câu filter test; nạp lại không nhân đôi; chi phí **$0** (model local). Test n=5 nên mọi khác biệt trên test chỉ mang tính minh họa.

## Setup và chạy lại (Windows / Python 3.11+)

```bash
cd starter
python -m venv .venv
.venv\Scripts\activate            # bash: source .venv/Scripts/activate
pip install -r requirements.txt   # pypdf, chromadb, sentence-transformers
python scripts/build_manifest.py  # (đã chạy) sinh data/manifest.json từ PDF
python scripts/verify_benchmark.py# (đã chạy) kiểm chứng 20/20 evidence trên trang gold
python -m src.run                 # chạy toàn pipeline A/B/C, in summary, ghi results/
```

Lần chạy đầu sẽ tự tải model embedding (~470 MB) về cache HuggingFace; nếu `huggingface.co` bị chặn, đặt `HF_ENDPOINT=https://hf-mirror.com` trước khi chạy. Không cần API key, không cần Docker (vector store = Chroma local, lưu `results/chroma/` — đã gitignore, tự dựng lại khi chạy). Muốn dựng lại từ đầu: xóa `results/chroma/` rồi chạy `python -m src.run`.

Phiên bản đã dùng: `chromadb 1.5.9`, `sentence-transformers 5.7.0`, `pypdf 6.21.4`, Python 3.11.9 (Windows). Corpus PDF đã commit trong `data/` (giấy phép CC BY-NC 3.0 IGO cho phép chia sẻ phi thương mại có ghi nguồn; manifest ghi đầy đủ nguồn/DOI).

## Cấu trúc repo

```text
STUDENT.md                        # thông tin học viên (điền tên/MSSV trước khi nộp)
README.md                         # file này — cách setup/chạy/tóm tắt
starter/src/                      # pipeline: ingestion, chunking, embeddings, store, evaluation, run
starter/scripts/                  # build_manifest.py, verify_benchmark.py (+ check_setup.py của đề)
starter/requirements.txt          # dependencies (đã cập nhật cho Chroma + sentence-transformers)
data/                             # 2 PDF + manifest.json (nguồn, license, trang, ký tự)
benchmark/questions.json          # 20 câu + gold + evidence + filter (đã kiểm chứng)
benchmark/verification.json       # bằng chứng kiểm chứng evidence
artifacts/experiment_log.csv      # 3 cấu hình, giả thuyết, kết quả dev/test
results/                          # metrics, traces.jsonl, ingest_stats, idempotence_check,
                                  # coherence/grounding/metadata labels + audit samples
report/individual/2A202603384_HoangBaoNguyen.md   # báo cáo cá nhân (Hoàng Bảo Nguyên — 2A202603384)
```

## Điểm thiết kế đáng chú ý

- **Hit định nghĩa chặt**: chunk phải đúng (document, page) gold **và** chứa đủ evidence quote (chuẩn hóa); mọi trang khác chứa cùng quote được ghi nhận là gold thay thế hợp lệ — không tính hit khi chỉ khớp trang hoặc chỉ khớp từ.
- **C–B chỉ khác đúng một thứ**: cùng chunk, cùng model; C chỉ thêm `where report = ...` khi câu hỏi có filter (filter là input giả định do người dùng cung cấp trước, không rút từ gold).
- **Idempotence**: chunk ID deterministic (`doc:page:index:hash`) + upsert + xóa chunk lỗi thời; tái nạp 683/379/379 không đổi (`results/idempotence_check.json`).
- **Không fallback mock**: lỗi provider/model sẽ dừng pipeline với thông báo (`starter/src/embeddings.py`).
- **Trung thực**: mọi số trong README/báo cáo lấy từ `results/*`; nhãn thủ công do AI hỗ trợ chấm dưới giám sát học viên và được ghi rõ trong báo cáo (RULES.md).
