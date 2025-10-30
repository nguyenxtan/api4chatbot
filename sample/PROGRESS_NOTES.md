# PDF → Bullet Conversion Pipeline - Progress Notes

## FINAL GOAL
**Ra được bullet format ĐÚNG, ĐỦ, ĐẸP** từ PDF gốc
- Format reference: `sample/bullet.md`
- Input: PDF gốc hoặc N8N JSON extract
- Output: Bullet markdown file

---

## JOURNEY & APPROACHES TRIED

### Phase 1: PDF → Markdown → Bullet (PyMuPDF route) ❌
**Files used:** `sample/508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf`

**Problem discovered:**
- PDF có **encoding lỗi trong table text** (PyMuPDF extract: "Tr ưở 14 :2" thay vì "Xe Bãi")
- Lỗi này **nằm ở PDF structure itself**, không thể fix bằng code
- Watermark: "Người in: Trịnh Vũ Kim Chi..." - hardcode Y position 220-260

**Approaches tried:**
1. ❌ **Hardcode signature block removal** (Y: 220-260) - không scalable, khác file khác signature
2. ❌ **Regex-based heading detection** - table ordering issue (Bảng 02/03 swapped)
3. ❌ **Proximity-based table matching** - improved nhưng encoding lỗi vẫn còn
4. ❌ **Text cleaning with regex** - `Tr ưở 14 :2` → `Trư ở14:2` - vẫn không đúng

**Tại sao fail:**
- Lỗi encoding ở PDF source - PyMuPDF không recovery được
- Cần OCR hoặc source file khác để fix

**Files created during this phase:**
- `sample/test_cleaned_markdown.md`
- `sample/test_original_markdown.md`
- `sample/test_cleaned31_markdown.md`
- `sample/cleaned_508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch (29).pdf`
- `sample/cleaned_508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch (31).pdf`

---

### Phase 2: N8N Extract Route (Better Option) ✅

**Discovery:** N8N workflows (trong n8n) có thể extract PDF → JSON với **text sạch hơn!**

**Files:**
- `sample/extract_from_n8n.json` - V1 (gốc, 53,815 chars, 28x "Người in")
- `sample/extract_from_n8n_v2.json` - V2 (clean, 45,755 chars, 2x "Người in")

**Key findings:**
1. ✅ **Watermark ở V1:** "Người in" xuất hiện 28 lần (có chèn giữa bảng)
2. ✅ **Watermark ở V2:** Chỉ còn 2 lần (trang cuối) - bỏ qua không sao
3. ✅ **Encoding:** V2 có smart quotes (''', """) + Unicode chars đúng (Đ, Á, Ả) - không phải lỗi
4. ✅ **Tables:** Cả 31 bảng đều đủ + đúng trong V2
5. ✅ **Table structure:** Text-based (không phải HTML), nhưng readable:
   ```
   Bảng 02 Đơn vị tính: đồng/container
   Container khô Container lạnh
   TT Phương án làm hàng 20' 40' 45' 20' 40' & 45'
   1 Xe Bãi 497.000 882.000 1.031.000 646.000 1.136.000
   ```

---

## CURRENT PLAN

**Input:** `sample/extract_from_n8n_v2.json`
- Text sạch + đủ dữ liệu
- Watermark tối thiểu (chỉ 2x ở cuối, bỏ qua được)
- Tất cả 31 bảng + full content

**Processing steps:**
1. Load V2 JSON → extract text
2. Remove watermark (regex: `Người ký:.*?Ngày in:.*?\n`)
3. Parse sections + tables
4. Convert table text → bullet format:
   - Header → "Bảng XX"
   - "Phương án" + values → bullet points (• key → value)
   - Format: `┃ • Item → Value`

**Output:** Bullet format matching `sample/bullet.md`

---

## IMPORTANT NOTES

### Files to keep:
- `sample/extract_from_n8n.json` - V1 reference (chuẩn)
- `sample/extract_from_n8n_v2.json` - V2 clean (dùng để convert)
- `sample/bullet.md` - Reference output format

### Files to clean up:
- ❌ `sample/test_*.md` (debug files)
- ❌ `sample/cleaned_*.pdf` (old attempts)
- ❌ `sample/markdown_*.md` (old attempts)

### Why V2 is BETTER than PyMuPDF:
1. ✅ No encoding issues (unlike PDF extraction)
2. ✅ Complete data (31/31 tables)
3. ✅ Minimal watermark (only 2x at end)
4. ✅ Already text-extracted (no need for OCR)
5. ✅ Scalable (N8N can process any PDF)

---

## PIPELINE DECISION

**DO NOT use PyMuPDF extraction** - encoding issue unfixable
**USE N8N JSON V2 extraction** - clean + reliable

---

## CODE IMPLEMENTATION

Need to implement:
- Parser for text-based table format
- Watermark remover (regex)
- Bullet formatter (matching bullet.md style)
- API endpoint `/documents/bullet` to accept N8N V2 JSON text

No changes needed to cleanfile/markdown APIs - just focus on bullet conversion.
