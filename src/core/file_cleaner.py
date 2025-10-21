"""
File Cleaner: Remove watermarks, headers, and footers from PDF and DOCX files using pikepdf.
"""
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from loguru import logger

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    logger.warning("pikepdf not available - install with: pip install pikepdf")
    PIKEPDF_AVAILABLE = False

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
        """Clean PDF by removing watermarks, annotations, headers and footers using pikepdf.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (success: bool, message: str, output_path: Optional[str])
        """
        if not PIKEPDF_AVAILABLE:
            return False, "pikepdf not installed. Install with: pip install pikepdf", None

        logger.info(f"Cleaning PDF with pikepdf: {file_path.name}")

        try:
            # Open PDF with pikepdf
            with pikepdf.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                annotation_count = 0
                content_removed_count = 0

                logger.info(f"Processing {total_pages} pages")

                # Process each page
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        # Remove all annotations (watermarks, comments, etc)
                        if "/Annots" in page:
                            annots = page["/Annots"]
                            if annots is not None:
                                annotation_count += len(annots)
                                del page["/Annots"]
                                logger.debug(f"Page {page_num}: Removed {len(annots)} annotations")

                        # Remove header/footer by filtering content stream
                        # This removes text in top and bottom regions
                        if "/Contents" in page:
                            try:
                                content_removed = self._remove_header_footer_from_content(page, pdf)
                                content_removed_count += content_removed
                                if content_removed > 0:
                                    logger.debug(f"Page {page_num}: Removed {content_removed} header/footer elements")
                            except Exception as content_err:
                                logger.debug(f"Page {page_num}: Could not process content stream: {content_err}")
                                continue

                    except Exception as page_error:
                        logger.warning(f"Error processing page {page_num}: {page_error}")
                        continue

                logger.info(f"Removed {annotation_count} annotations and {content_removed_count} header/footer elements")

                # Save cleaned PDF
                output_filename = f"cleaned_{file_path.stem}.pdf"
                output_path = self.output_dir / output_filename

                # Save with compression
                pdf.save(str(output_path), compress_streams=True)

                # Check file sizes
                original_size = file_path.stat().st_size
                cleaned_size = output_path.stat().st_size
                size_reduction = ((original_size - cleaned_size) / original_size * 100) if original_size > 0 else 0

                logger.info(f"Original size: {original_size} bytes, Cleaned size: {cleaned_size} bytes, Reduction: {size_reduction:.1f}%")

                return (
                    True,
                    f"PDF cleaned successfully. Removed {annotation_count} annotations and {content_removed_count} header/footer elements.",
                    str(output_path)
                )

        except Exception as e:
            logger.error(f"Error cleaning PDF: {e}", exc_info=True)
            return False, f"Error cleaning PDF: {str(e)}", None

    def _remove_header_footer_from_content(self, page, pdf) -> int:
        """Remove header/footer content from page content stream.

        Strategy: Parse content streams as an array, track text positioning state,
        and filter out text drawing commands in top/bottom regions.

        Args:
            page: pikepdf page object
            pdf: pikepdf PDF object (needed for creating new streams)

        Returns:
            Count of elements removed
        """
        try:
            # Get page dimensions
            if "/MediaBox" not in page:
                return 0

            mediabox = page["/MediaBox"]
            page_height = float(mediabox[3]) - float(mediabox[1])
            page_width = float(mediabox[2]) - float(mediabox[0])

            # Define regions (top 10% and bottom 10% of page)
            header_threshold = page_height * 0.90  # Top 10%: y > 90% of height
            footer_threshold = page_height * 0.10  # Bottom 10%: y < 10% of height

            logger.debug(f"Page dimensions: {page_width} x {page_height}, header_threshold={header_threshold}, footer_threshold={footer_threshold}")

            # Get content stream(s)
            if "/Contents" not in page:
                return 0

            contents = page["/Contents"]
            if contents is None:
                return 0

            # Contents can be a single stream or an array of streams (pikepdf.Array)
            content_streams = []
            try:
                # Use isinstance to check if it's an array
                if isinstance(contents, pikepdf.Array):
                    # It's an array of streams
                    content_streams = list(contents)
                else:
                    # Single stream
                    content_streams = [contents]
            except:
                # Fallback: treat as single stream
                content_streams = [contents]

            # Process each stream and collect filtered content
            total_removed = 0
            new_streams = []

            for stream_idx, stream in enumerate(content_streams):
                try:
                    content_data = stream.read_bytes()
                    filtered_content = self._filter_content_stream(
                        content_data, header_threshold, footer_threshold, page_height
                    )

                    if filtered_content != content_data:
                        total_removed += 1
                        logger.debug(f"Filtered stream {stream_idx}: content changed")
                        # Create new stream with filtered content
                        # Note: pikepdf.Stream requires (pdf, bytes) not (page, bytes)
                        new_stream = pikepdf.Stream(pdf, filtered_content)
                        new_streams.append(new_stream)
                    else:
                        new_streams.append(stream)

                except Exception as stream_err:
                    logger.debug(f"Error processing stream {stream_idx}: {stream_err}, keeping original")
                    new_streams.append(stream)

            # Replace content streams if any were modified
            if total_removed > 0:
                if len(new_streams) == 1:
                    page["/Contents"] = new_streams[0]
                else:
                    page["/Contents"] = pikepdf.Array(new_streams)

            return total_removed

        except Exception as e:
            logger.debug(f"Error filtering content: {e}")
            return 0

    def _filter_content_stream(self, content: bytes, header_threshold: float, footer_threshold: float, page_height: float) -> bytes:
        """Filter content stream to remove header/footer text.

        Strategy: Parse PDF content operators, track text matrix (Tm), and skip
        text drawing commands (Tj, TJ) when text positioning indicates header/footer.

        Args:
            content: PDF content stream bytes
            header_threshold: Y position for top boundary
            footer_threshold: Y position for bottom boundary
            page_height: Total page height for context

        Returns:
            Filtered content bytes
        """
        try:
            content_str = content.decode('latin-1', errors='ignore')

            # Split into tokens/lines for processing
            lines = content_str.split('\n')
            filtered_lines = []
            current_text_y = None
            skip_next_text = False

            for i, line in enumerate(lines):
                line_stripped = line.strip()

                if not line_stripped:
                    filtered_lines.append(line)
                    continue

                # Track text positioning - Tm sets absolute position
                # Format: a b c d e f Tm (e=x, f=y in standard coordinates)
                if line_stripped.endswith('Tm'):
                    parts = line_stripped.split()
                    if len(parts) >= 6:
                        try:
                            # f is the Y coordinate (second to last token)
                            y_pos = float(parts[-3])
                            current_text_y = y_pos

                            # Check if this Y position is in header/footer region
                            if y_pos >= header_threshold or y_pos <= footer_threshold:
                                skip_next_text = True
                                logger.debug(f"Header/footer detected at Y={y_pos:.1f} (header_th={header_threshold:.1f}, footer_th={footer_threshold:.1f})")
                            else:
                                skip_next_text = False
                        except (ValueError, IndexError):
                            pass

                # Also track Td/TD (relative positioning)
                elif line_stripped.endswith('Td') or line_stripped.endswith('TD'):
                    skip_next_text = False  # Relative movements are usually small, reset

                # Skip text drawing operators if in header/footer region
                elif skip_next_text and (line_stripped.endswith('Tj') or line_stripped.endswith('TJ') or line_stripped.endswith('\'') or line_stripped.endswith('"')):
                    # Skip text operators in header/footer
                    logger.debug(f"Skipping text operator: {line_stripped[:60]}")
                    continue

                # Reset flag when we encounter graphics state changes
                elif line_stripped in ['q', 'Q', 'BT', 'ET']:
                    if line_stripped in ['q', 'Q']:
                        skip_next_text = False  # Graphics state change, reset

                filtered_lines.append(line)

            filtered_content = '\n'.join(filtered_lines)
            return filtered_content.encode('latin-1', errors='ignore')

        except Exception as e:
            logger.debug(f"Error in content filtering: {e}")
            return content

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
                for paragraph in list(header.paragraphs):
                    p = paragraph._element
                    p.getparent().remove(p)
                    header_count += 1

            # Remove footers from all sections
            footer_count = 0
            for section in doc.sections:
                footer = section.footer
                for paragraph in list(footer.paragraphs):
                    p = paragraph._element
                    p.getparent().remove(p)
                    footer_count += 1

            logger.info(f"Removed {header_count} headers and {footer_count} footers")

            # Save cleaned DOCX
            output_filename = f"cleaned_{file_path.stem}.docx"
            output_path = self.output_dir / output_filename
            doc.save(str(output_path))

            logger.info(f"Cleaned DOCX saved to: {output_path}")
            return (
                True,
                f"DOCX cleaned successfully. Removed {header_count} headers and {footer_count} footers.",
                str(output_path)
            )

        except Exception as e:
            logger.error(f"Error cleaning DOCX: {e}", exc_info=True)
            return False, f"Error cleaning DOCX: {str(e)}", None
