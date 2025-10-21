"""
File Cleaner: Remove watermarks, headers, and footers from PDF and DOCX files.
"""
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from loguru import logger

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    logger.warning("PyMuPDF not available")
    PYMUPDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    logger.warning("python-docx not available")
    PYTHON_DOCX_AVAILABLE = False


class FileCleaner:
    """Clean PDF and DOCX files by removing watermarks, headers, and footers."""

    def __init__(self, output_dir: str = "temp/cleaned"):
        """Initialize file cleaner.

        Args:
            output_dir: Directory to save cleaned files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clean_file(self, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """Clean a file (PDF or DOCX).

        Args:
            file_path: Path to the file to clean

        Returns:
            Tuple of (success: bool, message: str, output_path: Optional[str])
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return False, f"File not found: {file_path}", None

        ext = file_path.suffix.lower()

        try:
            if ext == ".pdf":
                return self._clean_pdf(file_path)
            elif ext == ".docx":
                return self._clean_docx(file_path)
            else:
                return False, f"Unsupported file format: {ext}. Only PDF and DOCX are supported.", None
        except Exception as e:
            logger.error(f"Error cleaning file: {e}", exc_info=True)
            return False, f"Error processing file: {str(e)}", None

    def _clean_pdf(self, file_path: Path) -> Tuple[bool, str, Optional[str]]:
        """Clean PDF by removing watermarks, annotations, headers and footers using hybrid approach.

        Uses multiple detection signals:
        1. Annotations (overlay watermarks)
        2. Position-based (top/bottom regions)
        3. Height-based (tall blocks = diagonal watermarks)
        4. Repetition-based (same block across pages = header/footer)
        5. Content-based (optional keywords)

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (success: bool, message: str, output_path: Optional[str])
        """
        if not PYMUPDF_AVAILABLE:
            return False, "PyMuPDF not installed. Install with: pip install pymupdf", None

        logger.info(f"Cleaning PDF: {file_path.name}")

        try:
            # Open PDF
            doc = fitz.open(file_path)

            annotation_count = 0
            header_footer_count = 0

            # Analyze document structure FIRST (before cleaning)
            # Track blocks across pages to find repeated ones (header/footer)
            block_signatures = {}  # signature -> [pages where it appears]

            # Phase 1: Analyze all pages to find patterns
            total_pages = len(doc)
            logger.info(f"=== PHASE 1: Analyzing {total_pages} pages ===")

            for page_num, page in enumerate(doc):
                try:
                    blocks = page.get_text("dict")["blocks"]
                    logger.debug(f"Page {page_num}: Found {len(blocks)} blocks")

                    for block_idx, block in enumerate(blocks):
                        if block["type"] == 0:  # Text block
                            # Create signature (position + text)
                            text = self._extract_block_text(block)
                            y0, y1 = block["bbox"][1], block["bbox"][3]
                            sig = (round(y0, 1), round(y1, 1), text[:50])

                            if sig not in block_signatures:
                                block_signatures[sig] = []
                            block_signatures[sig].append(page_num)

                            if page_num < 2:  # Log first 2 pages for debug
                                logger.debug(f"  Block {block_idx}: y={y0:.0f}-{y1:.0f}, text={text[:30]}")
                except Exception as e:
                    logger.error(f"Error analyzing page {page_num}: {e}", exc_info=True)
                    continue

            logger.info(f"Found {len(block_signatures)} unique block signatures")

            # Find repeated blocks (likely header/footer)
            repeated_blocks = {sig: pages for sig, pages in block_signatures.items()
                             if len(pages) > total_pages * 0.7}  # Appears in >70% of pages
            logger.info(f"Detected {len(repeated_blocks)} repeated blocks (>70% of {total_pages} pages)")

            for sig, pages in list(repeated_blocks.items())[:5]:  # Show first 5
                _, _, text = sig
                logger.info(f"  Repeated: '{text}' on pages {pages[:3]}...")

            # Phase 2: Clean each page
            logger.info(f"=== PHASE 2: Cleaning {total_pages} pages ===")
            for page_num, page in enumerate(doc, start=1):
                try:
                    # Remove annotations
                    annotation_count += self._remove_annotations(page, page_num)

                    # Remove header/footer blocks using hybrid approach
                    blocks = page.get_text("dict")["blocks"]
                    page_height = page.rect.height
                    page_width = page.rect.width

                    # Detect regions
                    header_threshold = page_height * 0.10  # Top 10%
                    footer_threshold = page_height * 0.90  # Bottom 10%

                    logger.debug(f"Page {page_num}: height={page_height:.0f}, header_threshold={header_threshold:.0f}, footer_threshold={footer_threshold:.0f}")

                    blocks_to_remove = []
                    for block_idx, block in enumerate(blocks):
                        if block["type"] == 0:  # Text block
                            # Collect signals
                            signals = []

                            block_text = self._extract_block_text(block)
                            y0, y1 = block["bbox"][1], block["bbox"][3]
                            x0, x1 = block["bbox"][0], block["bbox"][2]
                            block_height = y1 - y0
                            block_width = x1 - x0

                            # Signal 1: Position-based (top/bottom 10%)
                            if y1 < header_threshold:
                                signals.append(("position_header", 0.7))
                            elif y0 > footer_threshold:
                                signals.append(("position_footer", 0.7))

                            # Signal 2: Height-based (very tall = diagonal watermark)
                            if block_height > 150:
                                signals.append(("height_tall", 0.6))

                            # Signal 3: Repetition (same block across many pages)
                            sig = (round(y0, 1), round(y1, 1), block_text[:50])
                            if sig in repeated_blocks:
                                signals.append(("repetition", 0.9))  # Highest confidence

                            # Signal 4: Content keywords (optional enhancement)
                            footer_keywords = ['Nơi nhận', 'Người ký', 'Ký duyệt', 'Ngày in:', 'Người in:']
                            if any(kw in block_text for kw in footer_keywords):
                                signals.append(("keyword", 0.8))

                            # Signal 5: Font size (very small = might be header/footer)
                            avg_font_size = self._get_avg_font_size(block)
                            if avg_font_size < 8 or avg_font_size > 20:
                                signals.append(("font_size", 0.5))

                            # Voting: if >= 2 signals agree, remove block
                            if len(signals) >= 2:
                                blocks_to_remove.append(block)
                                if page_num <= 2:  # Log first 2 pages
                                    logger.info(f"  Page {page_num} Block {block_idx}: REMOVE - signals={[s[0] for s in signals]}, text='{block_text[:40]}'")
                            elif page_num <= 2 and len(signals) >= 1:
                                logger.debug(f"  Page {page_num} Block {block_idx}: KEEP ({len(signals)} signal, need 2) - text='{block_text[:40]}'")

                    logger.info(f"Page {page_num}: {len(blocks_to_remove)} blocks marked for removal")

                    # Remove marked blocks
                    for block in blocks_to_remove:
                        rect = fitz.Rect(block["bbox"])
                        page.draw_rect(rect, color=None, fill=fitz.pdfcolor.white)
                        header_footer_count += 1

                except Exception as page_error:
                    logger.error(f"Error processing page {page_num}: {page_error}", exc_info=True)
                    continue

            logger.info(f"Removed {annotation_count} annotations and {header_footer_count} header/footer blocks")

            # Save cleaned PDF
            output_filename = f"cleaned_{file_path.stem}.pdf"
            output_path = self.output_dir / output_filename
            doc.save(str(output_path))
            doc.close()

            logger.info(f"Cleaned PDF saved to: {output_path}")
            return (
                True,
                f"PDF cleaned successfully. Removed {annotation_count} annotations and {header_footer_count} header/footer blocks.",
                str(output_path)
            )

        except Exception as e:
            logger.error(f"Error cleaning PDF: {e}", exc_info=True)
            return False, f"Error cleaning PDF: {str(e)}", None

    def _extract_block_text(self, block: dict) -> str:
        """Extract text from PDF block."""
        text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text += span.get("text", "")
        return text.strip()

    def _get_avg_font_size(self, block: dict) -> float:
        """Get average font size of block."""
        sizes = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size", 0)
                if size > 0:
                    sizes.append(size)
        return sum(sizes) / len(sizes) if sizes else 12

    def _remove_annotations(self, page, page_num: int) -> int:
        """Remove annotations from page. Returns count removed."""
        count = 0
        try:
            if hasattr(page, 'get_annotations'):
                annotations = page.get_annotations()
            else:
                annotations = page.annots()

            if annotations:
                for annot in annotations:
                    try:
                        if hasattr(page, 'delete_annot'):
                            page.delete_annot(annot)
                        else:
                            annot_obj = page.get_annot(annot)
                            if annot_obj:
                                annot_obj.delete()
                        count += 1
                    except Exception as e:
                        logger.debug(f"Could not delete annotation on page {page_num}: {e}")
                        continue
        except Exception as e:
            logger.debug(f"Could not access annotations on page {page_num}: {e}")

        return count

    def _clean_docx(self, file_path: Path) -> Tuple[bool, str, Optional[str]]:
        """Clean DOCX by removing headers, footers, and watermarks.

        Args:
            file_path: Path to DOCX file

        Returns:
            Tuple of (success: bool, message: str, output_path: Optional[str])
        """
        if not PYTHON_DOCX_AVAILABLE:
            return False, "python-docx not installed. Install with: pip install python-docx", None

        logger.info(f"Cleaning DOCX: {file_path.name}")

        try:
            doc = DocxDocument(file_path)

            # Remove headers from all sections
            header_count = 0
            for section in doc.sections:
                header = section.header
                # Remove all paragraphs in header
                for paragraph in header.paragraphs:
                    p = paragraph._element
                    p.getparent().remove(p)
                    header_count += 1

            # Remove footers from all sections
            footer_count = 0
            for section in doc.sections:
                footer = section.footer
                # Remove all paragraphs in footer
                for paragraph in footer.paragraphs:
                    p = paragraph._element
                    p.getparent().remove(p)
                    footer_count += 1

            # Remove watermarks from document
            # Watermarks in DOCX are stored in header as VML shapes
            watermark_count = 0
            for section in doc.sections:
                # Check header for watermark shapes
                header_part = section.header._element
                # Find and remove watermark elements
                for child in header_part.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pict',
                                                  namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}):
                    header_part.remove(child)
                    watermark_count += 1

            logger.info(f"Removed {header_count} headers, {footer_count} footers, {watermark_count} watermarks")

            # Save cleaned DOCX
            output_filename = f"cleaned_{file_path.stem}.docx"
            output_path = self.output_dir / output_filename
            doc.save(str(output_path))

            logger.info(f"Cleaned DOCX saved to: {output_path}")
            return (
                True,
                f"DOCX cleaned successfully. Removed {header_count} headers, {footer_count} footers, {watermark_count} watermarks.",
                str(output_path)
            )

        except Exception as e:
            logger.error(f"Error cleaning DOCX: {e}", exc_info=True)
            return False, f"Error cleaning DOCX: {str(e)}", None
