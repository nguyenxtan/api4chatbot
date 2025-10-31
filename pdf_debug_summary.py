#!/usr/bin/env python3
"""
Additional PDF Analysis - Focusing on Header/Footer Detection Issues
"""

import fitz  # PyMuPDF

def detailed_analysis(pdf_path):
    """Provide detailed analysis of why header/footer removal might fail"""

    print("=" * 80)
    print("DETAILED HEADER/FOOTER REMOVAL DEBUGGING ANALYSIS")
    print("=" * 80)

    doc = fitz.open(pdf_path)

    # Analyze first 3 pages
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]

        print(f"\n\nPAGE {page_num + 1} DETAILED ANALYSIS:")
        print("-" * 80)

        height = page.rect.height
        header_threshold = height * 0.15
        footer_threshold = height * 0.85

        print(f"Page height: {height:.2f}")
        print(f"Header boundary (15%): y < {header_threshold:.2f}")
        print(f"Footer boundary (15%): y > {footer_threshold:.2f}")

        # Get all text blocks
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [b for b in blocks if b.get("type") == 0]

        print(f"\n🔍 CRITICAL FINDINGS:")
        print("-" * 80)

        # Issue 1: Check for overlapping content
        header_blocks = []
        footer_blocks = []
        overlapping_blocks = []

        for block in text_blocks:
            bbox = block["bbox"]
            y0, y1 = bbox[1], bbox[3]

            # Extract text
            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "") + " "
            text = text.strip()

            # Check if block spans multiple regions
            in_header = y0 < header_threshold
            in_footer = y1 > footer_threshold
            crosses_header = y0 < header_threshold and y1 >= header_threshold
            crosses_footer = y0 <= footer_threshold and y1 > footer_threshold

            if crosses_header or crosses_footer:
                overlapping_blocks.append({
                    'y0': y0, 'y1': y1, 'text': text[:80],
                    'crosses_header': crosses_header,
                    'crosses_footer': crosses_footer
                })
            elif in_header:
                header_blocks.append({'y0': y0, 'y1': y1, 'text': text[:80]})
            elif in_footer:
                footer_blocks.append({'y0': y0, 'y1': y1, 'text': text[:80]})

        # Report overlapping blocks (MAJOR ISSUE)
        if overlapping_blocks:
            print(f"\n⚠️  ISSUE #1: Found {len(overlapping_blocks)} blocks that SPAN across boundaries!")
            print("These blocks might be removed even though they contain body content:")
            for i, b in enumerate(overlapping_blocks, 1):
                region = "HEADER→BODY" if b['crosses_header'] else "BODY→FOOTER"
                print(f"  {i}. [{region}] Y: {b['y0']:.2f} → {b['y1']:.2f}")
                print(f"     Text: {repr(b['text'])}")
        else:
            print("\n✓ No overlapping blocks found")

        # Issue 2: Check watermark position
        print(f"\n⚠️  ISSUE #2: Watermark analysis")
        watermark_found = False
        for block in text_blocks:
            bbox = block["bbox"]
            y0, y1 = bbox[1], bbox[3]

            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "") + " "
            text = text.strip()

            # Check if this looks like a watermark
            if "Người in:" in text or "Ngày in:" in text or "chitvk@saigonnewport.com.vn" in text:
                watermark_found = True
                block_height = y1 - y0
                print(f"  Found watermark/metadata block:")
                print(f"    Y-position: {y0:.2f} → {y1:.2f} (height: {block_height:.2f})")
                print(f"    Text preview: {repr(text[:100])}")

                # Determine which region it falls into
                if y0 < header_threshold:
                    print(f"    ⚠️  WARNING: Watermark y0 ({y0:.2f}) is in HEADER region (< {header_threshold:.2f})")
                elif y1 > footer_threshold:
                    print(f"    ⚠️  WARNING: Watermark y1 ({y1:.2f}) is in FOOTER region (> {footer_threshold:.2f})")
                else:
                    print(f"    Status: Watermark is in BODY region (should NOT be removed)")

                # Check if it spans a large vertical area
                if block_height > 200:
                    print(f"    ⚠️  CRITICAL: This watermark is {block_height:.2f} points tall!")
                    print(f"       This suggests it's diagonal/rotated text spanning multiple regions")

        if not watermark_found:
            print("  No watermark blocks detected on this page")

        # Issue 3: Company header repetition
        print(f"\n⚠️  ISSUE #3: Repeating header/footer content")
        company_header = "TỔNG CÔNG TY TÂN CẢNG SÀI GÒN"
        footer_text = "Biểu giá dịch vụ tại cảng Tân Cảng"

        has_company_header = False
        has_footer_text = False

        for block in text_blocks:
            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "") + " "
            text = text.strip()

            if company_header in text:
                has_company_header = True
                bbox = block["bbox"]
                y0 = bbox[1]
                print(f"  Company header found at y={y0:.2f}")
                if y0 < header_threshold:
                    print(f"    ✓ Correctly in header region (will be removed)")
                else:
                    print(f"    ⚠️  NOT in header region (won't be removed!)")

            if footer_text in text:
                has_footer_text = True
                bbox = block["bbox"]
                y1 = bbox[3]
                print(f"  Footer text found at y={y1:.2f}")
                if y1 > footer_threshold:
                    print(f"    ✓ Correctly in footer region (will be removed)")
                else:
                    print(f"    ⚠️  NOT in footer region (won't be removed!)")

        # Issue 4: Content that should NOT be removed
        print(f"\n⚠️  ISSUE #4: Important content in header/footer regions")

        important_patterns = [
            "QUYẾT ĐỊNH",
            "Điều 1:", "Điều 2:", "Điều 3:",
            "I. QUY ĐỊNH CHUNG",
            "BIỂU GIÁ DỊCH VỤ"
        ]

        for block in text_blocks:
            bbox = block["bbox"]
            y0, y1 = bbox[1], bbox[3]

            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "") + " "
            text = text.strip()

            # Check if important content is in header/footer region
            for pattern in important_patterns:
                if pattern in text:
                    if y0 < header_threshold:
                        print(f"  ⚠️  '{pattern}' found in HEADER region at y={y0:.2f}")
                        print(f"      This important content WILL BE REMOVED!")
                        print(f"      Text: {repr(text[:80])}")
                    elif y1 > footer_threshold:
                        print(f"  ⚠️  '{pattern}' found in FOOTER region at y={y1:.2f}")
                        print(f"      This important content WILL BE REMOVED!")
                        print(f"      Text: {repr(text[:80])}")

    # Final recommendations
    print("\n\n" + "=" * 80)
    print("RECOMMENDATIONS FOR FIXING HEADER/FOOTER REMOVAL:")
    print("=" * 80)
    print("""
1. ADJUST THRESHOLD PERCENTAGES:
   - Current: 15% header, 15% footer (85% threshold)
   - Suggested: Try 8-10% for header, 8-10% for footer
   - This will reduce false positives (important content being removed)

2. IMPROVE BLOCK DETECTION:
   - Use y0 (top of block) for header detection
   - Use y1 (bottom of block) for footer detection
   - Don't remove blocks that SPAN across boundaries

3. ADD CONTENT-BASED FILTERING:
   - Don't remove blocks containing important keywords:
     * "Điều", "QUYẾT ĐỊNH", "QUY ĐỊNH CHUNG", "BIỂU GIÁ"
   - Only remove blocks with known header/footer patterns:
     * Company headers, page numbers, date footers

4. HANDLE WATERMARKS SEPARATELY:
   - Detect rotated/diagonal text (large bbox height)
   - Remove watermarks based on content match, not position

5. USE TWO-PASS APPROACH:
   - Pass 1: Identify repeating elements across ALL pages
   - Pass 2: Only remove elements that appear on EVERY page

6. TEST WITH CONSERVATIVE SETTINGS FIRST:
   - Start with 5% header/footer regions
   - Add content whitelist (important terms to never remove)
   - Gradually adjust based on results
""")

    doc.close()

if __name__ == "__main__":
    pdf_path = "/Users/tannx/Documents/chatbot/api4chatbot/sample/508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf"
    detailed_analysis(pdf_path)
