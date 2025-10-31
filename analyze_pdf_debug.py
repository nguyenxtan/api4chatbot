#!/usr/bin/env python3
"""
PDF Structure Analysis Script for Debugging Header/Footer Removal
"""

import fitz  # PyMuPDF
import sys

def analyze_pdf(pdf_path):
    """Analyze PDF structure to debug header/footer removal"""

    print(f"Analyzing PDF: {pdf_path}\n")
    print("=" * 80)

    try:
        doc = fitz.open(pdf_path)
        print(f"Total pages in document: {len(doc)}")
        print("=" * 80 + "\n")

        # Analyze first 3 pages
        pages_to_analyze = min(3, len(doc))

        for page_num in range(pages_to_analyze):
            page = doc[page_num]
            print(f"\n{'#' * 80}")
            print(f"PAGE {page_num + 1} ANALYSIS")
            print(f"{'#' * 80}\n")

            # Get page dimensions
            rect = page.rect
            width = rect.width
            height = rect.height
            print(f"Page Dimensions: {width:.2f} x {height:.2f} points")
            print(f"Page Rect: {rect}")

            # Calculate header and footer regions (15% each)
            header_threshold = height * 0.15
            footer_threshold = height * 0.85

            print(f"\nRegion Thresholds:")
            print(f"  Header region: y < {header_threshold:.2f} (top 15%)")
            print(f"  Footer region: y > {footer_threshold:.2f} (bottom 15%)")
            print(f"  Body region: {header_threshold:.2f} < y < {footer_threshold:.2f}")

            # Extract text blocks
            blocks = page.get_text("dict")["blocks"]
            text_blocks = [b for b in blocks if b.get("type") == 0]  # Type 0 = text blocks

            print(f"\nTotal text blocks: {len(text_blocks)}")

            # Categorize blocks
            header_blocks = []
            footer_blocks = []
            body_blocks = []

            print("\n" + "-" * 80)
            print("TEXT BLOCKS WITH POSITIONS:")
            print("-" * 80)

            for idx, block in enumerate(text_blocks):
                bbox = block["bbox"]
                x0, y0, x1, y1 = bbox

                # Extract text from lines
                text_content = []
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_content.append(span.get("text", ""))

                full_text = " ".join(text_content).strip()

                # Categorize block
                region = "BODY"
                if y0 < header_threshold:
                    region = "HEADER"
                    header_blocks.append((block, full_text))
                elif y1 > footer_threshold:
                    region = "FOOTER"
                    footer_blocks.append((block, full_text))
                else:
                    body_blocks.append((block, full_text))

                print(f"\nBlock {idx + 1} [{region}]:")
                print(f"  BBox: ({x0:.2f}, {y0:.2f}, {x1:.2f}, {y1:.2f})")
                print(f"  Y-range: {y0:.2f} to {y1:.2f}")
                print(f"  Text: {repr(full_text[:100])}")
                if len(full_text) > 100:
                    print(f"  ... (truncated, total length: {len(full_text)} chars)")

            # Summary of regions
            print("\n" + "=" * 80)
            print("REGION SUMMARY:")
            print("=" * 80)

            print(f"\nHEADER REGION (top 15%, y < {header_threshold:.2f}):")
            print(f"  Found {len(header_blocks)} text blocks")
            if header_blocks:
                for i, (block, text) in enumerate(header_blocks, 1):
                    print(f"  {i}. {repr(text[:80])}")
            else:
                print("  (No text blocks in header region)")

            print(f"\nFOOTER REGION (bottom 15%, y > {footer_threshold:.2f}):")
            print(f"  Found {len(footer_blocks)} text blocks")
            if footer_blocks:
                for i, (block, text) in enumerate(footer_blocks, 1):
                    print(f"  {i}. {repr(text[:80])}")
            else:
                print("  (No text blocks in footer region)")

            print(f"\nBODY REGION (middle 70%):")
            print(f"  Found {len(body_blocks)} text blocks")

            # Check for annotations/watermarks
            print("\n" + "-" * 80)
            print("ANNOTATIONS & WATERMARKS:")
            print("-" * 80)

            annots = page.annots()
            annot_count = 0
            if annots:
                for annot in annots:
                    annot_count += 1
                    print(f"  Annotation {annot_count}:")
                    print(f"    Type: {annot.type}")
                    print(f"    Rect: {annot.rect}")
                    info = annot.info
                    if info.get("content"):
                        print(f"    Content: {info['content'][:100]}")

            print(f"\nTotal annotations: {annot_count}")

            # Check for drawings/images
            drawings = page.get_drawings()
            images = page.get_images()
            print(f"Total drawings: {len(drawings)}")
            print(f"Total images: {len(images)}")

            if images:
                print("\nImages found:")
                for img_idx, img in enumerate(images, 1):
                    print(f"  Image {img_idx}: xref={img[0]}")

        doc.close()

    except Exception as e:
        print(f"Error analyzing PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    pdf_path = "/Users/tannx/Documents/chatbot/api4chatbot/sample/508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf"
    analyze_pdf(pdf_path)
