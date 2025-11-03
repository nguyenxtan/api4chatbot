# DEVELOPMENT & PIPELINE - api4chatbot

**Purpose**: Single source of truth for the exact pipeline and technical decisions.
**Last Updated**: 2025-11-03
**Status**: LOCKED - Follow this pipeline ONLY

---

## 🎯 FINAL PIPELINE (DO NOT DEVIATE)

```
Official PDF
    ↓
markdown.md (cleaned, verified against PDF)
    ↓
/documents/bullet API endpoint
    ↓
bullet_v4.md (final output)
```

### Rules (Non-Negotiable):
1. **Source of Truth**: Official PDF file
2. **Intermediate Format**: markdown.md with proper markdown tables (not text-based)
3. **Data Flow**: Must go through /documents/bullet API (NO manual patching)
4. **Output**: bullet_v4.md is the only valid output
5. **extract_from_n8n_v2.json**: Reference only, NOT primary source (text-based format loses data)

---

## 📋 FILES IN USE

### Keep in Sample Folder:
- `508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf` - Official source document
- `extract_from_n8n_v2.json` - Reference data (for reference only)
- `markdown.md` - Cleaned markdown version (verified against PDF)
- `bullet_v4.md` - Final output from API pipeline

### Delete from Sample Folder:
- ❌ `bullet_v3.md` - Old manual version (violates pipeline rule)
- ❌ `parse_json_to_md.py` - Not needed
- ❌ `generate_markdown.py` - Not needed
- ❌ Any other intermediate files

---

## 🔄 STEP-BY-STEP WORKFLOW

### When Starting Fresh:

1. **Start with PDF**
   ```
   Source: /Users/tannx/Documents/chatbot/api4chatbot/sample/508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf
   Status: ✓ Already verified - no errors
   ```

2. **Use Cleaned markdown.md**
   ```
   File: /Users/tannx/Documents/chatbot/api4chatbot/sample/markdown.md
   Status: ✓ Fixed 2025-11-03
   - Added missing rows (IMDG, OOG nhóm 1)
   - Fixed text wrapping issues
   - Removed orphan headers
   - Matches PDF exactly
   ```

3. **Call /documents/bullet API**
   ```
   Input: markdown.md content
   Endpoint: POST /documents/bullet
   Request Body: { "text": "markdown content here" }
   Output: bullet_v4.md with proper structure
   ```

4. **Verify bullet_v4.md**
   - Bảng 01: All pricing data present
   - Bảng 02: TT2 with ghi chú notes
   - Section 1.1.4.a: All 5 container types (IMDG, OOG1, OOG2, OOG+IMDG, chuyên dụng)

---

## 🛠️ API ENDPOINT DETAILS

### /documents/bullet Endpoint
**Location**: `src/api.py`
**Request Model**: `BulletRequest` with `text` field
**Converter Used**: `MarkdownToBulletConverter` from `src/core/markdown_to_bullet.py`

**Auto-Detection Logic**:
- If has "Bảng XX" markers AND has markdown pipes `|` → use markdown table parser
- If has "Bảng XX" but NO pipes → use text-based parser (⚠️ data loss risk)

**Current Status**:
- Input: markdown.md (has proper markdown tables with pipes)
- Converter path: markdown_tables parser ✓
- Data loss: NONE ✓

---

## 📊 DATA INTEGRITY CHECKLIST

When using /documents/bullet API:

- [ ] Input file is markdown.md (not extract_from_n8n_v2.json)
- [ ] markdown.md matches official PDF
- [ ] Bảng 01 pricing data is present
- [ ] Bảng 02 TT2 ghi chú is included
- [ ] Section 1.1.4.a has all 5 container types
- [ ] No text wrapping or broken lines
- [ ] No orphan headers

---

## ❌ WHAT NOT TO DO

**FORBIDDEN**:
1. ❌ Manual patching of bullet_v4.md
2. ❌ Using extract_from_n8n_v2.json as primary source
3. ❌ Mixing data from multiple sources
4. ❌ Creating new markdown versions without PDF verification
5. ❌ Deviating from this pipeline

**If data is missing**:
1. Fix the source (markdown.md)
2. Verify against PDF
3. Re-run through /documents/bullet API
4. Do NOT manually patch output

---

## 🔍 TECHNICAL NOTES

### markdown.md Structure
```
### 1.1.4. Các trường hợp phụ thu
### a. Đối với container IMDG, container OOG...

| TT | Loại container | Phương án làm hàng |  |
| --- | --- | --- | --- |
|  |  | Tàu/ Sà lan  Bãi | Xe  Bãi |
| 1 | IMDG | Tăng 50% ... | Tăng 100% ... |
| 2 | OOG nhóm 1 (*) | Tăng 50% ... | Tăng 200% ... |
...
```

### Key Points
- Markdown tables must have pipes `|` for proper parsing
- No text wrapping (all content on single line)
- Headers use ### format
- Table structure: Header row → separator → data rows

---

## 📝 BEFORE EVERY CODE SESSION

Read this section before coding:

1. **What is the pipeline?**
   - PDF → markdown.md → /documents/bullet API → bullet_v4.md

2. **Is markdown.md clean?**
   - Check: matches PDF exactly (verify table 1.1.4.a has 5 rows)

3. **Are we using the right API endpoint?**
   - Check: POST /documents/bullet with markdown.md content

4. **Will the output be correct?**
   - Check: converter detects markdown tables (has pipes)
   - Result: markdown_tables parser used, no data loss

---

## 🎓 IMPORTANT LEARNING POINTS

**Why This Pipeline?**
1. PDF is official source (100% trustworthy)
2. markdown.md is verified (matches PDF exactly)
3. /documents/bullet API enforces data flow rules
4. No manual patching = data integrity guaranteed
5. Single source of truth = no confusion

**Why NOT extract_from_n8n_v2.json?**
- Text-based format loses table structure
- Auto-detection chooses text-based parser
- Results in missing data (IMDG, OOG nhóm 1 rows)
- Higher risk of data loss

---

**Version**: 1.0 (LOCKED)
**Created**: 2025-11-03
**Status**: Ready for implementation
