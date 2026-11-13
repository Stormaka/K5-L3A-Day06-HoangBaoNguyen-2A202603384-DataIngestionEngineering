# Checklist rà soát nhãn thủ công (học viên xác nhận trước khi nộp)

Đánh dấu `[x]` vào cột **Đồng ý** sau khi đã đọc nhãn + lý do và đối chiếu với dữ liệu gốc.
Nếu không đồng ý: sửa điểm trong file nhãn tương ứng và ghi lý do vào cột Ghi chú.
Giải thích chi tiết từng nhãn (tiếng Việt): `results/label_explanations_vi.md`.

## 1. Grounding (15 nhãn) — nguồn: `results/grounding_audit.json`

| Câu | Chiến lược | Điểm | Lý do | Đồng ý | Ghi chú |
|---|---|---|---|---|---|
| q16 | A | 2 | top-2 = ts2023 p32 with full forecast sentence incl '6.0 percent in 2025'; source traceable | [x] | |
| q16 | B | 1 | top-2/3 = ts2024 forecasts (6.5% 2025-26): forecast evidence present but WRONG report for the question | [x] | |
| q16 | C | 0 | filter applied correctly (all ts2023) but no chunk contains any 2025 forecast | [x] | |
| q17 | A | 2 | top-2 = ts2024 p31 chunk containing full 7.9% + restructured loans + VAMC sentence | [x] | |
| q17 | B | 0 | top-3 all ts2023 unrelated (financing needs, net errors); no problem-loan evidence | [x] | |
| q17 | C | 0 | identical results to B (no filter on this question) | [x] | |
| q18 | A | 1 | top-2 has Dec-2023 level 24,258 but only to Mar-2024 (24,760); missing end-June 25,334 | [x] | |
| q18 | B | 1 | top-1 = ts2024 p14 SBV response: direction/devaluation % present, but no Dec->Jun levels | [x] | |
| q18 | C | 1 | identical to B (no filter) | [x] | |
| q19 | A | 1 | p40 window cut right before the number ('...remains small'); topic yes, figure no | [x] | |
| q19 | B | 2 | p40 chunk has equivalent evidence 'institutional investors remains smaller than most regional peers at 19 percent of GDP' (grader-confirmed alternative) | [x] | |
| q19 | C | 2 | identical to B (no filter) | [x] | |
| q20 | A | 2 | top-1 = ts2024 p23 with full 'IPI reaching 166 (+14.3 percent (y/y))' | [x] | |
| q20 | B | 2 | top-1 = ts2024 p23 paragraph containing the same sentence | [x] | |
| q20 | C | 2 | identical to B (no filter) | [x] | |

## 2. Coherence (30 nhãn, mẫu 10 trang nội dung) — nguồn: `results/coherence_sample.json`

| Vị trí | Chiến lược | Điểm | Lý do | Đồng ý | Ghi chú |
|---|---|---|---|---|---|
| ts2023:p11 | A | 0.89 | 9 windows cut mid-word/mid-sentence ('stering', 'cent (y/y)'); footnote fragment | [x] | |
| ts2023:p11 | B | 2.0 | 6 chunks = complete paragraphs, heading prefix kept | [x] | |
| ts2023:p12 | A | 1.0 | 10 windows mostly mid-sentence; 56-char trailing fragment | [x] | |
| ts2023:p12 | B | 1.86 | 7 complete paragraphs; one has footnote '5' text glued | [x] | |
| ts2023:p13 | A | 1.0 | 9 windows all mid-sentence/mid-word starts; table fragment tail | [x] | |
| ts2023:p13 | B | 1.75 | 3 complete outlook/CPI paragraphs + 1 chunk mixed with garbled table data | [x] | |
| ts2023:p14 | A | 1.0 | 9 windows mid-word starts ('ly, the financial sector', '3 percent (y/y)') | [x] | |
| ts2023:p14 | B | 1.8 | 4 complete risk/fiscal paragraphs; recommendation chunk has 'z' bullets + footnote glue | [x] | |
| ts2023:p15 | A | 1.1 | page opens with footnotes 10/11 mixed into windows; 9 of 10 windows mid-sentence | [x] | |
| ts2023:p15 | B | 1.8 | complete paragraphs; first chunk contains page-leading footnote block | [x] | |
| ts2023:p16 | A | 1.0 | 10 windows mid-sentence; footnote fragment tail | [x] | |
| ts2023:p16 | B | 1.86 | 6 complete paragraphs; last has footnotes 15/16 glued | [x] | |
| ts2023:p17 | A | 0.9 | 10 windows mid-sentence; 88-char orphan fragment at end | [x] | |
| ts2023:p17 | B | 1.83 | 5 complete recommendation paragraphs; first has footnote 17 + CCDR glue | [x] | |
| ts2023:p19 | A | 1.0 | prose windows mid-sentence; figure axis data and footnotes mixed in | [x] | |
| ts2023:p19 | B | 1.67 | 2 complete chapter-opening paragraphs; footnote block chunk | [x] | |
| ts2023:p20 | A | 1.0 | starts mid-sentence ('year strong post-COVID rebound'); figure data in windows | [x] | |
| ts2023:p20 | B | 1.4 | 2 complete paragraphs; chunks with figure labels / footnote 21 tails score lower | [x] | |
| ts2023:p21 | A | 1.0 | 7 windows all mid-sentence/mid-word; final window is figure axis labels | [x] | |
| ts2023:p21 | B | 1.75 | 3 complete paragraphs; one figure-label chunk | [x] | |

(C dùng lại nguyên văn chunk của B — nhãn C ≡ B theo thiết kế.)

## 3. Metadata (45 bản ghi) — nguồn: `results/metadata_audit_labels.csv`

- [x] 45/45 bản ghi có đủ `document_id/source/page/report/year` và giá trị khớp nguồn
- [x] Filter compliance 3/3 trên câu q16 (chiến lược C) khớp trace trong `traces.jsonl`

## 4. Số liệu đối chiếu chéo

- [x] Bảng kết quả trong báo cáo khớp `results/metrics.json` (Hit@1/Hit@3 từng chiến lược)
- [x] Số chunk 683/379/379 khớp `results/ingest_stats.json` và `idempotence_check.json`
