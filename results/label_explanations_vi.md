# Giải thích chi tiết 39 ô tick trong `label_review_checklist.md`

Mỗi ô dưới đây ghi: nhãn hiện tại → vì sao đồng ý → xem bằng chứng ở đâu.
Người đọc: học viên Hoàng Bảo Nguyên. Mục tiêu: đọc ~10 phút là hiểu và tự quyết tick.

## A. Grounding — 15 ô (nguồn đối chiếu: `results/grounding_audit.json`)

| # | Ô | Nhãn | Vì sao đồng ý |
|---|---|---|---|
| 1 | q16 / A | 2 | Chunk xếp hạng 2 của A là ts2023 trang 32, chứa nguyên câu "...slow projected recovery to 5.5 percent in 2024 and to 6.0 percent in 2025" → trả lời trọn câu hỏi (2025 = 6,0%) + truy được nguồn |
| 2 | q16 / B | 1 | Top-2 và top-3 của B là ts2024 (dự báo 6,1% năm 2024, 6,5% 2025–26): CÓ bằng chứng dự báo nhưng SAI báo cáo — câu hỏi chỉ định báo cáo August 2023 → đúng định nghĩa mức 1 "có nhưng thiếu ngữ cảnh" |
| 3 | q16 / C | 0 | C lọc đúng 100% ts2023 (cả 3 chunk đều ts2023, thấy trong trace) nhưng KHÔNG chunk nào chứa dự báo năm 2025 → đúng mức 0 "không có bằng chứng" |
| 4 | q17 / A | 2 | Chunk hạng 2 (ts2024 p31) chứa đủ câu "total problem loans could be as high as 7.9 percent if restructured loans and ... (VAMC) debts are included" → đủ cả con số lẫn điều kiện |
| 5 | q17 / B | 0 | Cả 3 kết quả của B đều từ ts2023 (nhu cầu vốn đầu tư, net errors and omissions, footnote vùng Đông Nam Bộ) — không liên quan problem loans → 0 |
| 6 | q17 / C | 0 | Câu không có filter nên C chạy hệt B (trace giống nhau từng byte) → 0 |
| 7 | q18 / A | 1 | Chunk hạng 2 (ts2024 p28) có mức "VND 24,258 in December 2023 to VND 24,760 by the end of March 2024" — có điểm đầu và hướng đi nhưng THIẾU mức cuối 25.334 (end-June 2024) → mức 1 |
| 8 | q18 / B | 1 | Top-1 của B (ts2024 p14) mô tả SBV giảm giá VND 3,6% nhưng không có mức tỷ giá cụ thể nào → mức 1 |
| 9 | q18 / C | 1 | Không filter → hệt B → mức 1 |
| 10 | q19 / A | 1 | Cửa sổ 500 ký tự của A trên trang 40 kết thúc ngay tại "...remains small" — con số "at 19 percent of GDP" rơi sang cửa sổ kế tiếp (mở chunk trong audit file là thấy ngay) → có chủ đề, thiếu con số → mức 1 |
| 11 | q19 / B | 2 | Chunk trang 40 của B chứa "institutional investors remains smaller than most regional peers at 19 percent of GDP" — evidence TƯƠNG ĐƯƠNG với gold (GUIDE cho phép "bằng chứng tương đương được người chấm xác nhận") → mức 2 |
| 12 | q19 / C | 2 | Không filter → hệt B → mức 2 |
| 13 | q20 / A | 2 | Top-1 của A (ts2024 p23) chứa "Industrial Production Index (IPI) reaching 166 (+14.3 percent (y/y))" → đủ |
| 14 | q20 / B | 2 | Chunk p23 của B chứa y câu trên (đoạn nguyên vẹn) → mức 2 |
| 15 | q20 / C | 2 | Không filter → hệt B → mức 2 |

## B. Coherence — 20 ô (nguồn đối chiếu: `results/coherence_sample.json`)

Quy luật chung để kiểm nhanh: chiến lược A ≈ 1,0 mọi trang vì cửa sổ 500 ký tự
hầu như luôn bắt đầu GIỮA từ / GIỮA câu; B 1,4–2,0 vì đoạn nguyên vẹn, chỉ
bị trừ ở chunk dính footnote hoặc nhãn trục hình (lỗi trích xuất PDF).

| # | Vị trí | A | B | Vì sao đồng ý |
|---|---|---|---|---|
| 1 | ts2023:p11 | 0,89 | 2,00 | A: cửa sổ bắt đầu "stering 8 percent…" (mất nửa chữ), "cent (y/y)…", cộng mảnh footnote 115 ký tự cuối trang. B: 6 chunk = 6 đoạn văn hoàn chỉnh, mỗi chunk có heading prefix |
| 2 | ts2023:p12 | 1,00 | 1,86 | B có 1/7 chunk dính text footnote "5 Private Sector Development Committee, April 2023" — bị trừ đúng chỗ |
| 3 | ts2023:p13 | 1,00 | 1,75 | B: 3 đoạn outlook/CPI nguyên vẹn; 1 chunk lẫn chuỗi số bảng (PDF extraction), bị trừ |
| 4 | ts2023:p14 | 1,00 | 1,80 | B: 4 đoạn risk/fiscal hoàn chỉnh; 1 chunk khuyến nghị có bullet "z" + footnote 9 dính |
| 5 | ts2023:p15 | 1,10 | 1,80 | Trang mở đầu bằng block footnote 10/11 — B gom được vào 1 chunk duy nhất (bị trừ 1 chỗ), phần còn lại nguyên vẹn |
| 6 | ts2023:p16 | 1,00 | 1,86 | B: chunk cuối dính footnote 15/16, 6 chunk còn lại hoàn chỉnh |
| 7 | ts2023:p17 | 0,90 | 1,83 | A có mảnh mồ côi 88 ký tự cuối trang (0 điểm); B: chunk đầu dính footnote 17 + CCDR |
| 8 | ts2023:p19 | 1,00 | 1,67 | B: 2 đoạn mở chương nguyên vẹn (2,0) + 1 block footnote (1,0) → trung bình 1,67 |
| 9 | ts2023:p20 | 1,00 | 1,40 | B bị 3/5 chunk kéo điểm: 2 chunk chứa nhãn trục hình ("H1-18 H1-19…", PDF song ngữ) + 1 chunk footnote 21 |
| 10 | ts2023:p21 | 1,00 | 1,75 | B: 3 đoạn nguyên vẹn + 1 chunk toàn nhãn hình |

(C không có ô riêng: C lưu y nguyên chunk của B — ghi chú đã có sẵn trong checklist.)

## C. Metadata — 2 ô (nguồn: `results/metadata_audit_labels.csv`, `results/traces.jsonl`)

- **Ô 16 — 45/45 bản ghi đủ & đúng:** file có đúng 45 dòng (5 câu test × 3 chiến lược × top-3), cột kết quả đều "OK" (đủ `document_id, source, page, report, year`); audit độc lập đã đối chiếu từng `chunk_id` với traces.jsonl — 0 lệch.
- **Ô 17 — Filter compliance 3/3 trên q16:** trong trace q16/chiến lược C, cả 3 chunk trả về đều `report = ts2023`, khớp filter câu hỏi; audit độc lập xác minh thêm trên cả 4 câu filter: 4/4.

## D. Đối chiếu số liệu — 2 ô (nguồn: `results/metrics.json`, `results/ingest_stats.json`, `results/idempotence_check.json`)

- **Ô 18 — Bảng Hit@1/Hit@3 trong báo cáo khớp metrics.json:** 6 ô số (A/B/C × dev/test) khớp; audit độc lập đã tính lại từ trace thô và khớp 100%.
- **Ô 19 — Số chunk 683/379/379:** khớp ingest_stats.json; idempotence_check.json cho thấy số lượng không đổi sau khi nạp lại (không trùng lặp).

---

## Sau khi đọc xong

1. Mở `results/label_review_checklist.md`, đổi `[ ]` → `[x]` ở những dòng BẠN đồng ý (tất cả 39 nếu bạn chấp nhận giải thích ở trên).
2. Dòng nào không thuyết phục: KHÔNG tick — ghi chú lý do ở cột cuối, hoặc yêu cầu sửa điểm trong file nhãn tương ứng (điều này được khuyến khích, thể hiện rà soát thật).
3. Commit + push:
   ```bash
   git add -A && git commit -m "Confirm manual labels via review checklist" && git push
   ```
