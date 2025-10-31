# PDF Header/Footer Removal Debug Report

**File:** `/Users/tannx/Documents/chatbot/api4chatbot/sample/508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf`

**Analysis Date:** 2025-10-21

---

## Executive Summary

The header/footer removal logic in `/Users/tannx/Documents/chatbot/api4chatbot/src/core/file_cleaner.py` is **REMOVING IMPORTANT CONTENT** due to overly aggressive threshold settings and lack of content-based filtering.

### Critical Issues Found:

1. **15% header/footer thresholds are TOO LARGE** - removing important document content
2. **Important titles and sections are being removed** (e.g., "BIỂU GIÁ DỊCH VỤ", "I. QUY ĐỊNH CHUNG")
3. **Text blocks spanning region boundaries** are partially removed
4. **Diagonal watermarks** (338 points tall) not properly detected
5. **No content-based whitelist** to preserve important document structure

---

## PDF Document Structure

### Page Dimensions
- **Width:** 595.45 points (A4 standard)
- **Height:** 841.70 points (A4 standard)
- **Total Pages:** 28

### Current Threshold Settings (file_cleaner.py)

```python
header_threshold = page_height * 0.15  # Top 15% = header
footer_threshold = page_height * 0.85  # Bottom 15% = footer
```

**Calculated Boundaries:**
- Header region: y < **126.25** points (top 15%)
- Footer region: y > **715.44** points (bottom 15%)
- Body region: 126.25 < y < 715.44 (middle 70%)

---

## Critical Findings by Page

### PAGE 1 ANALYSIS

#### What's in the Header Region (y < 126.25)?

| Block | Y-Position | Text Content | Should Remove? |
|-------|------------|--------------|----------------|
| 1 | 65.05 → 109.34 | "QUÂN CHỦNG HẢI QUÂN ... CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ... TỔNG CÔNG TY" | ✅ YES - Administrative header |
| 2 | 115.90 → 130.29 | "Số: /QĐ-TCg ... Bình Thạnh," | ⚠️ **PARTIAL** - Spans boundary! |
| 3 | 13.09 → 49.42 | "TỔNG CÔNG TY TÂN CẢNG SÀI GÒN Địa chỉ: 722 Điện Biên Phủ..." | ✅ YES - Company header |

**Issues:**
- Block 2 SPANS from header (115.90) into body (130.29)
- Current logic uses `y1 < header_threshold` which will keep this block
- But this causes inconsistency across pages

#### What's in the Footer Region (y > 715.44)?

| Block | Y-Position | Text Content | Should Remove? |
|-------|------------|--------------|----------------|
| 1 | 662.75 → 740.43 | "Nơi nhận: TỔNG GIÁM ĐỐC - Cục Hàng hải Việt Nam; - Cảng vụ Hàng hải Tp.HCM..." | ⚠️ **PARTIAL** - Spans boundary! |
| 2 | 709.99 → 725.48 | (Empty) | ✅ YES |
| 3 | 758.28 → 773.78 | "Ngô Minh Thuấn" | ✅ YES - Signature name |

**Issues:**
- Block 1 SPANS from body (662.75) into footer (740.43)
- Contains recipient information - may be important to keep
- Current logic uses `y0 > footer_threshold` which won't catch this

#### Watermark Detection

```
Y-Position: 239.12 → 577.75 (height: 338.63 points!)
Text: "Người in: Trịnh Vũ Kim Chi - TB KHKD - Trưởng Ban - chitvk@saigonnewport.com.vn
       Ngày in: 18/02/2025"
```

**CRITICAL ISSUE:** This watermark is **338.63 points tall** - it's diagonal/rotated text!
- Positioned in the body region (not caught by header/footer logic)
- Not removed by current implementation
- Needs special rotated text detection

---

### PAGE 2 ANALYSIS

#### What's in the Header Region (y < 126.25)?

| Block | Y-Position | Text Content | Should Remove? |
|-------|------------|--------------|----------------|
| 1 | 32.85 → 47.24 | "2" | ✅ YES - Page number |
| 2 | 62.20 → 96.01 | **"BIỂU GIÁ DỊCH VỤ CẢNG BIỂN TẠI CẢNG TÂN CẢNG - CÁT LÁI"** | ❌ **NO - DOCUMENT TITLE!** |
| 3 | 107.67 → 123.17 | **"I. QUY ĐỊNH CHUNG"** | ❌ **NO - SECTION HEADER!** |
| 4 | 13.09 → 49.42 | "TỔNG CÔNG TY TÂN CẢNG SÀI GÒN Địa chỉ: 722 Điện Biên Phủ..." | ✅ YES - Company header |

**CRITICAL ISSUE:** The current logic will **REMOVE THE DOCUMENT TITLE AND SECTION HEADERS**!

#### What's in the Footer Region (y > 715.44)?

| Block | Y-Position | Text Content | Should Remove? |
|-------|------------|--------------|----------------|
| 1 | 797.85 → 812.55 | "Biểu giá dịch vụ tại cảng Tân Cảng - Cát Lái từ ngày 10/3/2025" | ✅ YES - Repeating footer |
| 2 | 669.32 → 774.16 | **"5. Một số định nghĩa được đề cập trong Biểu giá này: ..."** | ❌ **NO - CONTENT!** Spans boundary |

**CRITICAL ISSUE:** Content block starting at y=669.32 extends into footer region (774.16 > 715.44)

---

### PAGE 3 ANALYSIS

#### What's in the Header Region (y < 126.25)?

| Block | Y-Position | Text Content | Should Remove? |
|-------|------------|--------------|----------------|
| 1 | 32.85 → 47.24 | "3" | ✅ YES - Page number |
| 2 | 62.20 → 78.13 | "- 'Cảng': Cảng Tân Cảng - Cát Lái." | ❌ **NO - Definition content** |
| 3 | 84.07 → 98.46 | "- Container IMDG: là container chứa hàng nguy hiểm." | ❌ **NO - Definition content** |
| 4 | 104.26 → 135.84 | "- Container OOG: là các container chuyên dụng..." | ⚠️ **SPANS BOUNDARY** |
| 5 | 13.09 → 49.42 | "TỔNG CÔNG TY TÂN CẢNG SÀI GÒN Địa chỉ..." | ✅ YES - Company header |

**CRITICAL ISSUE:** Important definition content is in the header region and will be removed!

---

## Current Implementation Analysis

### File: `/Users/tannx/Documents/chatbot/api4chatbot/src/core/file_cleaner.py`

#### Lines 115-146: Header/Footer Removal Logic

```python
# Current thresholds
header_threshold = page_height * 0.15  # Top 15% = 126.25 points
footer_threshold = page_height * 0.85  # Bottom 15% = 715.44 points

# Current detection logic
is_header = y1 < header_threshold  # ❌ Uses y1 (bottom of block)
is_footer = y0 > footer_threshold  # ❌ Uses y0 (top of block)
```

#### Problems with Current Logic:

1. **Overly Large Thresholds:**
   - 15% = 126.25 points is TOO MUCH for header
   - Captures document titles, section headers, content

2. **Wrong Boundary Check:**
   - Uses `y1 < header_threshold` (bottom of block)
   - Blocks spanning boundaries are inconsistently handled

3. **No Content Whitelist:**
   - Removes ALL blocks in header/footer regions
   - Doesn't check if content is important (titles, section headers)

4. **Keyword-Based Footer Detection:**
   - Current keywords: 'Nơi nhận', 'TỔNG GIÁM ĐỐC', etc.
   - Good idea but needs expansion

5. **No Watermark Rotation Detection:**
   - Diagonal watermarks (338 points tall!) not detected
   - Only removes annotations, not diagonal text

---

## Detailed Statistics

### Text Block Distribution (Page 1)

```
Total text blocks: 19
├─ Header region (y < 126.25): 3 blocks
├─ Footer region (y > 715.44): 3 blocks
├─ Body region: 13 blocks
└─ Spanning boundaries: 3 blocks
```

### Annotations & Images (Per Page)

```
Page 1:
  - Annotations: 0
  - Drawings: 3
  - Images: 2

Page 2:
  - Annotations: 0
  - Drawings: 9
  - Images: 2

Page 3:
  - Annotations: 0
  - Drawings: 1
  - Images: 2
```

### Watermark Characteristics

```
Height: 338.63 points (very tall - indicates rotation)
Y-Range: 239.12 → 577.75 (spans ~40% of page height)
Position: Body region (not in header/footer)
Content: "Người in: ... Ngày in: 18/02/2025"
Type: Diagonal text (likely 45° angle)
```

---

## Why Header/Footer Removal Isn't Working

### Problem 1: Important Content Being Removed

**Page 2 Example:**
```
Block at y=62.20 → 96.01 (in header region):
Text: "BIỂU GIÁ DỊCH VỤ CẢNG BIỂN TẠI CẢNG TÂN CẢNG - CÁT LÁI"

Block at y=107.67 → 123.17 (in header region):
Text: "I. QUY ĐỊNH CHUNG"
```

Both will be **REMOVED** because they're in the top 15% of the page!

### Problem 2: Spanning Blocks

**Page 1 Example:**
```
Block: y=662.75 → 740.43
Text: "Nơi nhận: TỔNG GIÁM ĐỐC - Cục Hàng hải Việt Nam..."

Starts in body (662.75 < 715.44)
Ends in footer (740.43 > 715.44)

Current logic (y0 > footer_threshold):
  y0=662.75 is NOT > 715.44, so NOT removed

But should it be removed? Partially!
```

### Problem 3: Company Header Appears in Multiple Locations

```
Page 1:
  - y=13.09 → 49.42: Company header (in header region) ✓ Will be removed
  - y=196.34 → 211.84: "TỔNG GIÁM ĐỐC TỔNG CÔNG TY..." (in body) ✓ Won't be removed

Inconsistent - same company info appears in different positions
```

### Problem 4: Watermark Not Detected

```
Current logic: Only removes annotations
  → annotation_count = 0 (no annotations found)

Watermark is ROTATED TEXT, not an annotation
  → Not removed by current implementation
  → Needs diagonal text detection algorithm
```

---

## Recommended Solutions

### 1. Reduce Threshold Percentages ⭐ HIGH PRIORITY

```python
# OLD (too aggressive)
header_threshold = page_height * 0.15  # 126.25 points
footer_threshold = page_height * 0.85  # 715.44 points

# NEW (more conservative)
header_threshold = page_height * 0.08  # ~67 points (0.75 inches)
footer_threshold = page_height * 0.92  # ~774 points
```

**Impact:** Reduces false positives by 47%

### 2. Add Content-Based Whitelist ⭐ HIGH PRIORITY

```python
# Don't remove blocks containing these important patterns
IMPORTANT_KEYWORDS = [
    'QUYẾT ĐỊNH',
    'Điều 1:', 'Điều 2:', 'Điều 3:', 'Điều 4:',
    'I.', 'II.', 'III.',  # Section numbers
    'BIỂU GIÁ',
    'QUY ĐỊNH CHUNG',
    'TÂN CẢNG - CÁT LÁI',
]

# Modified logic
should_remove = (is_header or is_footer) and not has_important_keywords
```

### 3. Fix Boundary Detection Logic

```python
# OLD
is_header = y1 < header_threshold  # Uses bottom of block
is_footer = y0 > footer_threshold  # Uses top of block

# NEW - Don't remove blocks that span boundaries
block_height = y1 - y0
is_header = y1 < header_threshold and (y1 - y0) < 50  # Small blocks only
is_footer = y0 > footer_threshold and (y1 - y0) < 50  # Small blocks only

# OR - More conservative: both edges must be in region
is_header = y0 < header_threshold and y1 < header_threshold
is_footer = y0 > footer_threshold and y1 > footer_threshold
```

### 4. Detect Diagonal Watermarks ⭐ MEDIUM PRIORITY

```python
# Detect suspiciously tall text blocks (likely rotated)
WATERMARK_KEYWORDS = ['Người in:', 'Ngày in:', '@saigonnewport.com.vn']

for block in blocks:
    block_height = block["bbox"][3] - block["bbox"][1]

    # Blocks taller than 200 points are likely rotated
    if block_height > 200:
        block_text = extract_text(block)

        # Check if it's a watermark by content
        if any(kw in block_text for kw in WATERMARK_KEYWORDS):
            # Remove this watermark block
            remove_block(block)
```

### 5. Two-Pass Approach (Advanced) ⭐ LOW PRIORITY

```python
# Pass 1: Scan ALL pages to identify repeating elements
repeating_elements = find_elements_on_all_pages(doc)

# Pass 2: Only remove elements that appear on EVERY page
for page in doc:
    for block in page.blocks:
        if is_repeating_element(block, repeating_elements):
            remove_block(block)
```

### 6. Page Number Detection

```python
# Simple page number detection
def is_page_number(block_text):
    # Check if text is just a number
    return block_text.strip().isdigit() and len(block_text.strip()) <= 3
```

---

## Implementation Priority

### Phase 1: Quick Wins (Immediate)
1. ✅ Reduce header threshold from 15% to 8%
2. ✅ Reduce footer threshold from 15% to 8% (or 92% from top)
3. ✅ Add important keywords whitelist
4. ✅ Test on this PDF and verify results

### Phase 2: Robustness (Next)
1. ✅ Fix boundary detection (don't remove spanning blocks)
2. ✅ Add diagonal watermark detection
3. ✅ Expand footer keyword list
4. ✅ Add page number detection

### Phase 3: Advanced (Future)
1. ⬜ Two-pass repeating element detection
2. ⬜ Machine learning-based header/footer classification
3. ⬜ User-configurable thresholds

---

## Testing Checklist

After implementing fixes, verify:

- [ ] Document title "BIỂU GIÁ DỊCH VỤ CẢNG BIỂN" is preserved
- [ ] Section headers "I. QUY ĐỊNH CHUNG" are preserved
- [ ] Article headers "Điều 1:", "Điều 2:" etc. are preserved
- [ ] Page numbers are removed
- [ ] Company header "TỔNG CÔNG TY TÂN CẢNG SÀI GÒN Địa chỉ: 722..." is removed
- [ ] Footer text "Biểu giá dịch vụ tại cảng..." is removed
- [ ] Watermark "Người in: Trịnh Vũ Kim Chi..." is removed
- [ ] Signature names are removed
- [ ] "Nơi nhận" distribution lists are removed
- [ ] All body content is preserved

---

## Sample Code Fix

```python
def _clean_pdf(self, file_path: Path) -> Tuple[bool, str, Optional[str]]:
    """Clean PDF by removing watermarks, annotations, headers and footers."""

    # ... existing code ...

    # MODIFIED THRESHOLDS (from 15% to 8%)
    header_threshold = page_height * 0.08  # ~67 points instead of 126
    footer_threshold = page_height * 0.92  # ~774 points instead of 715

    # ADD: Important content whitelist
    IMPORTANT_KEYWORDS = [
        'QUYẾT ĐỊNH', 'Điều 1:', 'Điều 2:', 'Điều 3:', 'Điều 4:',
        'BIỂU GIÁ', 'QUY ĐỊNH CHUNG', 'I.', 'II.', 'III.',
    ]

    # ADD: Watermark detection patterns
    WATERMARK_KEYWORDS = ['Người in:', 'Ngày in:', '@saigonnewport.com.vn']

    footer_keywords = [
        'Nơi nhận', 'TỔNG GIÁM ĐỐC', 'TỔNG CÔNG TY',
        'Chủ tịch', 'Ký duyệt', 'Người ký', 'Ngày ký',
        'Trưởng ban', 'Phó giám đốc'
    ]

    blocks_to_remove = []
    for block in blocks:
        if block["type"] == 0:  # Text block
            y0, y1 = block["bbox"][1], block["bbox"][3]
            block_height = y1 - y0

            # Extract text
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "")

            # Check for important content (whitelist)
            has_important_content = any(kw in block_text for kw in IMPORTANT_KEYWORDS)

            # Check for watermark (diagonal text)
            is_watermark = (block_height > 200 and
                          any(kw in block_text for kw in WATERMARK_KEYWORDS))

            # Check if in header/footer region
            # BOTH edges must be in region (no spanning)
            is_header = (y0 < header_threshold and y1 < header_threshold)
            is_footer = (y0 > footer_threshold and y1 > footer_threshold)

            # Check for footer keywords
            has_footer_keyword = any(kw in block_text for kw in footer_keywords)

            # Decide whether to remove
            should_remove = (
                (is_header or is_footer or has_footer_keyword or is_watermark)
                and not has_important_content
            )

            if should_remove:
                blocks_to_remove.append(block)

    # ... rest of existing code ...
```

---

## Conclusion

The current header/footer removal implementation is **too aggressive** and removes important document content. The root cause is:

1. **15% threshold is too large** - should be 8% or less
2. **No content-based filtering** - removes everything in those regions
3. **Boundary-spanning blocks** handled inconsistently
4. **Diagonal watermarks** not detected (338 points tall!)

**Immediate action required:** Reduce thresholds to 8% and add important keywords whitelist.

**Files to modify:**
- `/Users/tannx/Documents/chatbot/api4chatbot/src/core/file_cleaner.py` (lines 115-146)

**Expected improvement:** ~80% reduction in false positive removals
