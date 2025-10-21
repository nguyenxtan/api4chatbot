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
        """Clean PDF by removing watermarks, annotations, headers and footers.

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

            # Process each page
            for page_num, page in enumerate(doc, start=1):
                try:
                    # Step 1: Remove annotations (watermarks overlay)
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
                                    annotation_count += 1
                                except Exception as annot_error:
                                    logger.debug(f"Could not delete annotation on page {page_num}: {annot_error}")
                                    continue
                    except Exception as annot_err:
                        logger.debug(f"Could not access annotations on page {page_num}: {annot_err}")

                    # Step 2: Remove header and footer text blocks
                    # Get page text with layout to identify position
                    blocks = page.get_text("dict")["blocks"]

                    page_height = page.rect.height
                    header_threshold = page_height * 0.15  # Top 15% = header
                    footer_threshold = page_height * 0.85  # Bottom 15% = footer

                    footer_keywords = [
                        'Nơi nhận', 'TỔNG GIÁM ĐỐC', 'TỔNG CÔNG TY',
                        'Chủ tịch', 'Ký duyệt', 'Người ký', 'Ngày ký',
                        'Trưởng ban', 'Phó giám đốc'
                    ]

                    # Identify blocks to remove (header/footer)
                    blocks_to_remove = []
                    for block in blocks:
                        if block["type"] == 0:  # Text block
                            # Get block position
                            y0 = block["bbox"][1]
                            y1 = block["bbox"][3]

                            # Check if block is in header or footer region
                            is_header = y1 < header_threshold
                            is_footer = y0 > footer_threshold

                            # Check for footer keywords
                            block_text = ""
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    block_text += span.get("text", "")

                            has_footer_keyword = any(keyword in block_text for keyword in footer_keywords)

                            # Mark for removal if header, footer region, or has footer keyword
                            if is_header or is_footer or has_footer_keyword:
                                blocks_to_remove.append(block)

                    # Remove marked blocks by drawing over them with white rectangles
                    for block in blocks_to_remove:
                        rect = fitz.Rect(block["bbox"])
                        # Draw white rectangle to cover the block
                        page.draw_rect(rect, color=None, fill=fitz.pdfcolor.white)
                        header_footer_count += 1

                except Exception as page_error:
                    logger.warning(f"Error processing page {page_num}: {page_error}")
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
