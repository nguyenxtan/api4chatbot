"""
Markdown to Bullet List Converter

Converts markdown content to bullet format with natural language arrow conversion.
Handles both markdown tables (with | pipes) and text-based tables from N8N extraction.
Formats output to match Vietnamese document standards with proper boxing and alignment.
"""

import re
import json
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from loguru import logger


class MarkdownToBulletConverter:
    """Convert markdown content to bullet list format with Vietnamese document styling"""

    def __init__(self):
        """Initialize converter with translation rules"""
        self.arrow_patterns = {
            '↔': '<->',
            '→': '->',
            '←': '<-',
        }
        # Box drawing characters
        self.box_chars = {
            'vertical': '┃',
            'top_left': '┌',
            'top_right': '┐',
            'bottom_left': '└',
            'bottom_right': '┘',
            'horizontal': '━',
            'cross': '┼',
            't_right': '┣',
            't_left': '┫',
            'separator': '━'
        }

    def _reorder_table_headings(self, markdown_content: str) -> str:
        """
        Fix markdown structure for proper table handling.

        Fixes two issues:
        1. Rejoin multi-line table cells that were split by PDF extraction
        2. Ensure 'Bảng XX' headings appear before their tables
        """
        lines = markdown_content.split('\n')

        # Step 1: Rejoin multi-line table cells
        # When a table row starts with |, subsequent lines that contain | are cell continuations
        result = []
        i = 0
        while i < len(lines):
            if lines[i].strip().startswith('|'):
                # This is a table row
                combined_row = lines[i]
                i += 1

                # Collect all continuation lines (those that don't start with | but are part of the row)
                # Look ahead to determine if subsequent lines are continuations or not
                while i < len(lines) and not lines[i].strip().startswith('|'):
                    # Peek at next lines to determine if we should keep collecting
                    # If next non-empty line doesn't start with | and has |, it's likely a continuation
                    # If it's empty or doesn't have |, check further ahead

                    current_line = lines[i]
                    if '|' in current_line:
                        # This line has pipes - likely a continuation
                        combined_row += ' ' + current_line.strip()
                        i += 1
                    elif current_line.strip() == '':
                        # Empty line - might be end of table, don't include
                        break
                    else:
                        # No pipes at start, might be continuation of previous cell
                        # Look ahead to find next line that either:
                        # 1. Starts with | (definitely a table row)
                        # 2. Has pipes (likely cell content continuation)
                        # 3. Is empty (gap in table)
                        next_idx = i + 1
                        found_table_or_continuation = False

                        while next_idx < len(lines):
                            next_line = lines[next_idx]
                            if next_line.strip().startswith('|'):
                                # Found another table row - current line is continuation
                                found_table_or_continuation = True
                                break
                            elif '|' in next_line:
                                # Found a line with pipes - likely cell continuation chain
                                found_table_or_continuation = True
                                break
                            elif next_line.strip() == '':
                                # Empty line - check further
                                next_idx += 1
                                continue
                            else:
                                # Non-table content - end of table row
                                break

                        if found_table_or_continuation:
                            # Current line is part of the table row
                            combined_row += ' ' + current_line.strip()
                            i += 1
                        else:
                            # Current line is not part of table - end of this row
                            break

                result.append(combined_row)
            else:
                result.append(lines[i])
                i += 1

        return '\n'.join(result)

    def convert(self, input_content: str) -> str:
        """
        Convert input content to bullet list format.

        Supports two formats:
        1. Markdown with pipe tables (|...)
        2. Text-based tables from N8N JSON extraction

        Args:
            input_content: Raw markdown text or plain text with tables

        Returns:
            Formatted bullet list text with proper Vietnamese document styling
        """
        logger.info("Starting conversion to bullet format")

        # Preprocess: Clean up section 1.1.4 formatting
        input_content = self._preprocess_section_114(input_content)

        # Check if input is N8N JSON format (has tables without markdown pipes)
        if self._is_text_based_table_format(input_content):
            logger.info("Detected text-based table format (N8N extraction)")
            return self._convert_text_based_tables(input_content)
        else:
            logger.info("Detected markdown table format")
            return self._convert_markdown_tables(input_content)
    def _preprocess_section_114(self, content: str) -> str:
        """
        Preprocess section 1.1.4 to fix formatting issues:
        1. Remove standalone '5' lines (orphan row numbers from page breaks)
        2. Remove page header lines ("Biểu giá dịch vụ...")
        3. Replace column headers with proper Vietnamese text
        4. Remove DUPLICATE header sequences (but keep the first one)
        """
        lines = content.split('\n')
        skip_indices = set()
        in_section_114 = False
        seen_first_header_sequence = False

        # First pass: identify which lines to skip
        for i, line in enumerate(lines):
            # Track if we're in section 1.1.4
            if '1.1.4' in line:
                in_section_114 = True
            elif re.match(r'^\d+\.\d+\.\s+', line):  # Next main section
                in_section_114 = False

            # Mark standalone '5' lines for skipping
            if in_section_114 and line.strip() == '5':
                skip_indices.add(i)

            # Mark page header lines for skipping
            if in_section_114 and 'Biểu giá dịch vụ tại cảng' in line and 'từ ngày' in line:
                skip_indices.add(i)

            # Detect and skip duplicate header sequences
            if in_section_114 and line.strip() == 'Phương án làm hàng':
                if i + 1 < len(lines) and lines[i+1].strip() == 'TT Loại container':
                    if seen_first_header_sequence:
                        # This is a duplicate, mark sequence for skipping (3-4 lines)
                        skip_indices.add(i)  # Phương án
                        skip_indices.add(i+1)  # TT Loại
                        if i + 2 < len(lines) and 'Tàu/' in lines[i+2] and 'Sà lan' in lines[i+2]:
                            skip_indices.add(i+2)  # Arrow headers
                    else:
                        seen_first_header_sequence = True

        # Second pass: build result, replacing column headers and skipping marked lines
        result = []
        in_section_114 = False

        for i, line in enumerate(lines):
            # Track section
            if '1.1.4' in line:
                in_section_114 = True
            elif re.match(r'^\d+\.\d+\.\s+', line):
                in_section_114 = False

            # Skip marked lines
            if i in skip_indices:
                continue

            # Replace column headers
            if in_section_114 and 'Tàu/' in line and 'Sà lan' in line and 'Bãi' in line:
                line1 = 'Từ tàu hoặc sà lan đến bãi hoặc từ bãi xuống tàu hoặc sà lan'
                line2 = 'Từ xe xuống bãi hoặc từ bãi lên xe'
                result.append(line1)
                result.append(line2)
                continue

            result.append(line)

        return '\n'.join(result)

    def _is_text_based_table_format(self, content: str) -> bool:
        """
        Detect if content uses text-based table format (N8N extraction)
        vs markdown table format.

        Text-based format has:
        - Lines starting with "Bảng XX"
        - No markdown pipe characters (|) for tables
        - Multi-line table structure with aligned columns
        """
        has_bang_markers = bool(re.search(r'^\s*Bảng\s+\d+', content, re.MULTILINE))
        has_markdown_tables = bool(re.search(r'^\s*\|', content, re.MULTILINE))

        return has_bang_markers and not has_markdown_tables

    def _convert_text_based_tables(self, content: str) -> str:
        """
        Convert text-based tables (N8N format) to bullet format.

        This handles tables that are formatted as plain text without markdown pipes.
        """
        # Remove watermark first
        content = self._remove_watermark(content)

        lines = content.split('\n')
        result = []
        i = 0
        last_section = None

        while i < len(lines):
            line = lines[i]

            # Skip empty lines at the start
            if not line.strip():
                if result and result[-1] != '':
                    result.append('')
                i += 1
                continue

            # Detect section headings (Roman numerals, numbered sections)
            if self._is_section_heading(line):
                section_heading = line.strip()
                result.append('')
                result.append(section_heading)
                result.append('━' * 80)
                last_section = section_heading
                i += 1
                continue

            # Detect subsection headings
            if self._is_subsection_heading(line):
                subsection = line.strip()
                result.append('')
                result.append(subsection)
                result.append('━' * min(len(subsection) + 2, 80))
                i += 1
                continue

            # Detect table start (Bảng XX)
            if re.match(r'^\s*Bảng\s+\d+', line):
                # Parse entire table and get next line index
                table_lines = [line]
                table_num = re.search(r'Bảng\s+(\d+)', line).group(1)
                i += 1

                # Collect table lines until we hit next section/heading
                while i < len(lines):
                    next_line = lines[i]

                    # Stop at next major section
                    if self._is_section_heading(next_line) or self._is_subsection_heading(next_line):
                        break

                    # Stop at next table
                    if re.match(r'^\s*Bảng\s+\d+', next_line):
                        break

                    table_lines.append(next_line)
                    i += 1

                # Parse and convert this table
                table_bullets = self._parse_text_table(table_lines, table_num)
                result.extend(table_bullets)
                continue

            # Check if we're in section 1.1.4 (Các trường hợp phụ thu) - skip implicit table detection here
            # Section 1.1.4 has complex nested structures that shouldn't be parsed as tables
            # Check both for section header and if we haven't exited via subsection d or next main section
            in_section_114 = False
            for prev_idx in range(max(0, i-50), i):
                if '1.1.4' in lines[prev_idx]:
                    in_section_114 = True
                # Exit section 1.1.4 if we hit subsection e, f or next section like 1.2., 1.3., etc.
                if re.match(r'^[e-z]\.\s+', lines[prev_idx]) or re.match(r'^\d+\.\d+\.\s+', lines[prev_idx]):
                    in_section_114 = False
                    break

            # Check if this is a table-like structure without "Bảng XX" header
            # This includes tables in section 1.1.4 (like mục a, b, c with implicit tables)
            # Pattern: "Phương án" line followed by "TT Loại container" line
            is_table_start = False
            if line.strip() and 'Phương án' in line:
                # Check next line for "TT Loại"
                if i + 1 < len(lines) and 'TT' in lines[i + 1] and 'Loại' in lines[i + 1]:
                    is_table_start = True

            if is_table_start:
                # Collect potential table lines
                potential_table = [line]
                temp_i = i + 1
                has_row_numbers = False
                has_prices = False

                # Look ahead to see if this looks like a table (allow longer tables for 1.1.4)
                while temp_i < len(lines) and len(potential_table) < 50:  # Increased from 20 to 50
                    next_line = lines[temp_i]

                    # Stop at next major section or table
                    if self._is_section_heading(next_line) or self._is_subsection_heading(next_line):
                        break
                    if re.match(r'^\s*Bảng\s+\d+', next_line):
                        break

                    # Also stop at lettered list items (a., b., c., etc.) which mark new subsections
                    if re.match(r'^[a-z]+\.\s+', next_line):
                        break

                    potential_table.append(next_line)

                    # Check for table indicators
                    if re.match(r'^\s*\d+\s+', next_line):  # Row numbers
                        has_row_numbers = True
                    if re.search(r'\d+\.\d{3}', next_line):  # Prices like 230.000
                        has_prices = True
                    if 'Thỏa thuận' in next_line:  # Special case
                        has_prices = True

                    temp_i += 1

                # If this looks like a table structure, parse it as a table
                if has_row_numbers and (has_prices or 'Thỏa thuận' in ''.join(potential_table)):
                    # This is a table without "Bảng XX" header
                    # Generate a table name based on current section
                    table_num = 'N/A'
                    table_bullets = self._parse_text_table(potential_table, table_num)
                    result.extend(table_bullets)
                    i = temp_i
                    continue

            # Regular content (descriptions, notes, etc.)
            if line.strip():
                # Skip metadata/signature lines
                if self._should_skip_line(line):
                    i += 1
                    continue

                # Check if we're still in section 1.1.4
                in_section_114_now = False
                for prev_idx in range(max(0, i-200), i):
                    if '1.1.4' in lines[prev_idx]:
                        in_section_114_now = True
                    # Exit section 1.1.4 when we hit next main section like 1.2.
                    if prev_idx > max(0, i-200) and re.match(r'^\d+\.\d+\.\s+', lines[prev_idx]) and '1.1.4' not in lines[prev_idx]:
                        in_section_114_now = False

                # Add as bullet point
                if line.strip().startswith(('-', '*', '•')):
                    result.append(line.strip())
                elif in_section_114_now:
                    # In section 1.1.4: only add bullet for subsection headers (a., b., c., d., etc.)
                    if re.match(r'^[a-d]\.\s+', line.strip()):
                        result.append('• ' + line.strip())
                    else:
                        # All other content in 1.1.4 - keep as plain text
                        result.append(line.strip())
                else:
                    # Normal content outside 1.1.4 - add bullet point
                    result.append('• ' + line.strip())

            i += 1

        output = '\n'.join(result)
        logger.info("Text-based table conversion completed")
        return output

    def _is_section_heading(self, line: str) -> bool:
        """Check if line is a main section heading (Roman numerals, I., II., etc.)"""
        return bool(re.match(r'^\s*(I+|[IVX]+)\.\s+[A-ZÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪ]', line))

    def _is_subsection_heading(self, line: str) -> bool:
        """Check if line is a subsection heading (numbered, 1., 1.1., etc.)"""
        return bool(re.match(r'^\s*\d+(\.\d+)?\.\s+[A-ZÀ-Ỿ]', line)) and not re.match(r'^\s*\d+\s+[A-ZÀ-Ỿ]', line)

    def _remove_watermark(self, content: str) -> str:
        """Remove watermark patterns from text"""
        # Remove "Người in", "Người ký", "Ngày in" patterns
        content = re.sub(r'Người\s+(?:in|ký)\s*:.*?(?=\n[A-Z]|\n\n|$)', '', content, flags=re.DOTALL)
        content = re.sub(r'Ngày\s+in\s*:.*?(?=\n[A-Z]|\n\n|$)', '', content, flags=re.DOTALL)
        return content

    def _should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped (metadata, signatures, etc.)"""
        skip_keywords = [
            'người in:', 'người ký:', 'thời gian', 'thủ trưởng',
            'ban chỉ huy', 'ct/tgđ', 'email', '.vn', 'điện thoại',
            'ngày in:', 'fax:', 'địa chỉ:', 'tổng công ty',
            'biểu giá dịch vụ tại cảng'
        ]
        return any(keyword in line.lower() for keyword in skip_keywords)

    def _parse_text_table(self, table_lines: List[str], table_num: str) -> List[str]:
        """
        Parse a text-based table and convert to bullet format.

        Expected format from N8N extraction:
        Bảng 02 Đơn vị tính: đồng/container
        Container khô Container lạnh
        TT Phương án làm hàng
        20' 40' 45' 20' 40' & 45'
        1 Xe Bãi 497.000 882.000 1.031.000 646.000 1.136.000
        298.000 528.000 627.000 596.000 1.018.000  <- prices for previous row
        2
        Hạ container ở tầng trên xuống đất phục vụ kiểm hoá.
        ...
        """
        if not table_lines:
            return []

        result = []

        # Extract table metadata from first line
        first_line = table_lines[0].strip()

        # Extract only the "Bảng XX" part, removing "Đơn vị tính..." suffix
        table_header = first_line
        # Match pattern like "Bảng 01" at the start
        match = re.match(r'(Bảng\s+\d+)', first_line)
        if match:
            table_header = match.group(1)

        result.append(table_header)
        result.append('━' * 80)
        result.append('')

        # Parse table structure: identify headers and data rows
        headers_tuple = self._extract_table_headers(table_lines)
        col_names = self._build_column_names(headers_tuple)

        # Check if this table is a "Bảng" table vs. implicit table without "Bảng XX" header
        # Bảng tables (like Bảng 01-31) should use "PHƯƠNG ÁN"
        # Implicit tables (like in section 1.1.4) without Bảng header should use "TT"
        is_bang_table = table_header.startswith('Bảng')

        # Also check: if the first line doesn't have Bảng, but has "Phương án", it's probably an implicit table
        if not is_bang_table and 'Phương án' in first_line:
            use_tt_format = True
        else:
            use_tt_format = False

        # Parse rows - more sophisticated handling of multi-line rows
        rows_data = self._extract_table_rows(table_lines)

        # Format as bullets
        for row_idx, row_data in enumerate(rows_data):
            # Include row if it has either description or prices
            description = row_data.get('description', '')
            prices = row_data.get('prices', [])

            if description or prices:
                row_num = row_data['num']

                # Check if prices are text-based (contain non-numeric words) vs numeric prices
                has_text_prices = any(price and not re.match(r'^\d+[\d.]*$', str(price).strip()) for price in prices if price)

                if has_text_prices:
                    # Text-based prices (like "Tăng 50%", "Thỏa thuận") - use PHƯƠNG ÁN format
                    result.append(f"┃ PHƯƠNG ÁN {row_num}: {description}")
                    result.append('┣' + '━' * 70)

                    # Add text prices as sub-bullets
                    if prices:
                        for col_idx, price in enumerate(prices):
                            if col_idx == 0:
                                result.append(f"┃ • Phương án làm hàng    → {price}")
                            else:
                                result.append(f"┃ •                      → {price}")
                    result.append('')
                else:
                    # Numeric prices - use TT format (original behavior)
                    result.append(f"┃ TT {row_num}: {description}")
                    result.append('┣' + '━' * 70)

                    # Add prices as sub-bullets
                    if prices:
                        for col_idx, price in enumerate(prices):
                            if col_idx < len(col_names):
                                col_name = col_names[col_idx]
                                result.append(f"┃ • {col_name:25} → {price}")
                            else:
                                result.append(f"┃ • {price}")

                    result.append('')

        # Collect and add any notes that appear after the table
        notes = []
        for i in range(1, len(table_lines)):
            line = table_lines[i].strip()
            if re.match(r'^\s*(ghi\s*chú|lưu\s*ý|chú\s*ý)\s*:', line, re.IGNORECASE):
                notes.append(line)

        # Add notes to output (outside the box)
        for note in notes:
            result.append(note)
            result.append('━' * 80)

        return result

    def _extract_table_headers(self, table_lines: List[str]) -> Tuple[str, str]:
        """
        Extract column headers from table lines.
        Returns (type_headers, size_headers) like ("Container khô Container lạnh", "20' 40' 45' 20' 40' & 45'")
        """
        type_header = ""
        size_header_parts = []

        for line in table_lines[1:6]:  # Look in first 5 lines after table title
            line = line.strip()
            if not line:
                continue

            # Skip data rows
            if re.match(r'^\d+\s+', line):
                continue

            # Check if this is the size line (contains multiple size patterns)
            if re.search(r"\d+[''ʼ\u2019]", line):
                size_header_parts.append(line)  # Append instead of overwrite
            # Check if this is the type line (contains khô or lạnh)
            elif 'khô' in line.lower() or 'lạnh' in line.lower():
                type_header = line

        # Join multi-line size headers with space
        size_header = ' '.join(size_header_parts) if size_header_parts else ""

        return (type_header, size_header)

    def _build_column_names(self, headers_tuple: Tuple[str, str]) -> List[str]:
        """Build column names from header information"""
        type_header, size_header = headers_tuple
        columns = []

        # Extract all sizes from size header
        all_sizes = re.findall(r"(\d+[''ʼ\u2019](?:\s*&\s*\d+[''ʼ\u2019])?)", size_header)

        if not all_sizes:
            return ["Price 1", "Price 2", "Price 3", "Price 4", "Price 5"]

        # Determine how many are for khô vs lạnh
        has_khô = 'khô' in type_header.lower()
        has_lạnh = 'lạnh' in type_header.lower()

        # Usually: 3 for khô (20', 40', 45') + 2 for lạnh (20', 40' & 45')
        # or: 3 for khô + remaining for lạnh
        num_khô = 3 if has_khô and has_lạnh else 0
        num_khô = len(all_sizes) if has_khô and not has_lạnh else num_khô

        # Build column names
        for i, size in enumerate(all_sizes):
            if i < num_khô:
                columns.append(f"Container khô {size}")
            else:
                columns.append(f"Container lạnh {size}")

        return columns if columns else ["Price 1", "Price 2", "Price 3", "Price 4", "Price 5"]

    def _extract_table_rows(self, table_lines: List[str]) -> List[Dict]:
        """
        Extract data rows from table lines.

        Handles complex cases where row data can be in various orders:

        Case 1:
        1 Xe Bãi 497.000 882.000 1.031.000 646.000 1.136.000
        (prices on same line as row number + description)

        Case 2:
        1 Xe Bãi 497.000 882.000 1.031.000 646.000 1.136.000
        298.000 528.000 627.000 596.000 1.018.000
        (additional continuation prices on next line)

        Case 3:
        2
        Hạ container ở tầng...
        298.000 528.000 627.000 596.000 1.018.000
        (row number alone, then description, then prices)
        """
        rows = []
        i = 1  # Skip first line (table title)
        pending_prices = None  # Prices from previous line that weren't assigned yet
        implicit_row_num = 0   # Counter for rows without explicit row numbers

        while i < len(table_lines):
            line = table_lines[i].strip()

            if not line:
                i += 1
                continue

            # Skip header lines and stop on section headings (end of table)
            if self._is_table_header_line(line) and not re.match(r'^\d+\s*$', line):
                i += 1
                continue

            # Stop processing table when we hit a section heading (1.1.3., 1.2., etc.)
            if self._is_section_heading(line):
                break

            # Stop processing table when we hit a note line (Ghi chú:, Lưu ý:, etc.)
            if re.match(r'^\s*(ghi\s*chú|lưu\s*ý|chú\s*ý)\s*:', line, re.IGNORECASE):
                break

            # Stop processing table when we hit a bullet point (•, -, *, etc.) which indicates new content/context
            # Include various Unicode bullet point characters (\uf0b7, \u2022, etc.)
            if re.match(r'^\s*[•\-*\uf0b7\u2022\u2023\u2043]\s+', line):
                break

            # Check if this is a data row (starts with digit)
            is_data_row = re.match(r'^\d+(\s|$)', line)

            if is_data_row:
                # Parse the row - could be single or multi-line
                row_data = self._parse_table_row_sequence(table_lines, i)
                if row_data:
                    # If we have pending prices from previous line, use them
                    if pending_prices and not row_data['prices']:
                        row_data['prices'] = pending_prices
                        pending_prices = None

                    rows.append(row_data)
                    i = row_data.get('next_idx', i + 1)

                    # Check if next line is just prices (for next row)
                    if i < len(table_lines):
                        next_line = table_lines[i].strip()
                        if next_line and not any(char.isalpha() for char in next_line if char not in '& '):
                            # This looks like a price line, save it for next row
                            pending_prices = self._extract_prices_from_line(next_line)
                            if pending_prices and len(pending_prices) >= 4:
                                i += 1  # Skip the price line, it will be used by next row
                            else:
                                pending_prices = None
                else:
                    i += 1
            else:
                # Check if this could be an implicit row (description without explicit row number)
                # E.g. in Bảng 03: "Giao/nhận container hàng quá cảnh." with no preceding row number
                row_data = self._parse_implicit_row(table_lines, i)
                if row_data:
                    implicit_row_num += 1
                    row_data['num'] = str(implicit_row_num)  # Assign implicit row number
                    rows.append(row_data)
                    i = row_data.get('next_idx', i + 1)
                else:
                    i += 1

        return rows

    def _is_section_heading(self, line: str) -> bool:
        """
        Detect if a line is a section heading (not a table row).

        Section headings follow patterns:
        - 1. Title
        - 1.1. Title
        - 1.1.1. Title
        - 1.1.3. Tác nghiệp...

        Table rows don't start with this pattern.
        """
        # Pattern: starts with digit, followed by . or digits and dots
        # Examples: "1. ", "1.1. ", "1.1.3. ", "2.1. "
        if re.match(r'^\d+(\.\d+)*\.\s+', line.strip()):
            return True
        return False

    def _parse_implicit_row(self, table_lines: List[str], start_idx: int) -> Optional[Dict]:
        """
        Parse a row without explicit row number (implicit row).

        Format:
        Giao/nhận container hàng
        quá cảnh.
        955.800 1.441.800 1.749.600 1.242.000 1.868.400

        Returns None if this doesn't look like an implicit row.
        """
        if start_idx >= len(table_lines):
            return None

        first_line = table_lines[start_idx].strip()

        # Check if this line could start a row (has text, not a header, not a section heading, not a note)
        if not first_line or self._is_table_header_line(first_line) or re.match(r'^\d+(\s|$)', first_line) or self._is_section_heading(first_line):
            return None

        # Reject note lines (Ghi chú:, Lưu ý:, etc.) - these mark end of table
        if re.match(r'^\s*(ghi\s*chú|lưu\s*ý|chú\s*ý)\s*:', first_line, re.IGNORECASE):
            return None

        # Collect lines until we hit prices or next row
        description_lines = [first_line]
        prices = []
        idx = start_idx + 1

        while idx < len(table_lines):
            curr_line = table_lines[idx].strip()

            if not curr_line:
                idx += 1
                continue

            # Check if this is next row, section heading, or note (end of table)
            if re.match(r'^\d+(\s|$)', curr_line) or self._is_table_header_line(curr_line) or self._is_section_heading(curr_line):
                break

            # Stop when we hit a note line
            if re.match(r'^\s*(ghi\s*chú|lưu\s*ý|chú\s*ý)\s*:', curr_line, re.IGNORECASE):
                break

            # Check if this is "Miễn phụ thu" (exempt from charges) - treat as a special price value
            if curr_line.lower().strip() == 'miễn phụ thu':
                # This is a non-numeric price status value that means no charges apply
                # Treat it as a single price value (like a status, not a numeric price)
                prices = ['Miễn phụ thu']  # Single status value for this row
                idx += 1
                break  # End of row data

            # Check if this line is prices (only numbers and dots)
            if not any(char.isalpha() for char in curr_line if char not in '& '):
                extracted_prices = self._extract_prices_from_line(curr_line)
                if extracted_prices and len(extracted_prices) >= 4:
                    prices = extracted_prices
                    idx += 1
                    break
                else:
                    # Not enough prices, treat as description
                    description_lines.append(curr_line)
                    idx += 1
            else:
                # Has text, likely description - but NOT "Miễn phụ thu" (already handled above)
                description_lines.append(curr_line)
                idx += 1

        # Clean up description and extract any mixed text-price lines
        clean_description_lines = []
        for line in description_lines:
            line_lower = line.lower()

            # Skip keywords that indicate metadata WITHIN a description
            # But preserve lines that START with "Ghi chú:", "Lưu ý:", etc. (these are NOTES)
            skip_keywords = [
                'cước đảo chuyển', 'lưu ý', 'chú ý',
                'dưới đây tại', 'tại bảng', 'theo quy định'
            ]

            # Check if line starts with a note indicator (should NOT be skipped)
            is_note_line = any(line_lower.startswith(kw + ':') for kw in ['ghi chú', 'lưu ý', 'chú ý'])

            # Skip lines that contain metadata WITHIN them (but not note lines)
            should_skip = not is_note_line and any(keyword in line_lower for keyword in skip_keywords)

            if not should_skip:
                # Check if this line mixes text and prices
                text_part, line_prices = self._split_text_and_prices(line)
                if line_prices and len(line_prices) >= 4:
                    # This line has prices - extract them
                    if text_part:
                        clean_description_lines.append(text_part)
                    if not prices:  # Only use these prices if we don't have prices yet
                        prices = line_prices[:5]
                else:
                    # No prices or not enough prices, keep whole line
                    clean_description_lines.append(line)

        description = ' '.join(clean_description_lines).strip()

        # Only return if we have either description or prices
        if description or prices:
            return {
                'num': '',  # Will be set by caller
                'description': description,
                'prices': prices[:5],
                'next_idx': idx
            }

        return None

    def _parse_table_row_sequence(self, table_lines: List[str], start_idx: int) -> Optional[Dict]:
        """
        Parse a complete table row that may span multiple lines.

        Format examples:
        1 Xe Bãi 497.000 882.000 1.031.000 646.000 1.136.000
        (optional: additional prices on next line)

        OR

        2
        Hạ container ở tầng trên xuống đất phục vụ kiểm hoá.
        (optional: more description)
        298.000 528.000 627.000 596.000 1.018.000
        """
        if start_idx >= len(table_lines):
            return None

        first_line = table_lines[start_idx].strip()

        # Pattern 1: Row number only (could be "2" or "3")
        if re.match(r'^\d+\s*$', first_line):
            row_num = first_line.strip()

            # Next line(s) are description, prices come later (or separately)
            description_lines = []
            prices = []
            idx = start_idx + 1

            # Collect description lines until we hit prices or next row
            while idx < len(table_lines):
                curr_line = table_lines[idx].strip()

                if not curr_line:
                    idx += 1
                    continue

                # Check if this is next row
                if re.match(r'^\d+\s*$', curr_line) or self._is_table_header_line(curr_line):
                    break

                # Check if this is "Miễn phụ thu" (exempt from charges) - treat as a special price value
                if curr_line.lower().strip() == 'miễn phụ thu':
                    # This is a non-numeric price status value that means no charges apply
                    # Treat it as a single price value (like a status, not a numeric price)
                    prices = ['Miễn phụ thu']  # Single status value for this row
                    idx += 1
                    break  # End of row data

                # Check if this line is prices (only numbers and dots)
                if not any(char.isalpha() for char in curr_line if char not in '& '):
                    extracted_prices = self._extract_prices_from_line(curr_line)
                    if extracted_prices and len(extracted_prices) >= 4:
                        # Found prices, don't include in description
                        prices = extracted_prices
                        idx += 1
                        break
                    else:
                        # Not enough prices, treat as description
                        description_lines.append(curr_line)
                        idx += 1
                else:
                    # Has text, likely description or text-based prices
                    description_lines.append(curr_line)
                    idx += 1

            # After collecting description lines, check if any are text-based prices
            # Text-based prices contain words like "Tăng", "Thỏa thuận", "Miễn", etc.
            if not prices:
                text_prices = []
                non_price_desc = []

                for line in description_lines:
                    # Check if this looks like a price (contains %, tăng, thỏa, miễn, etc.)
                    if any(keyword in line.lower() for keyword in ['tăng', 'thỏa thuận', 'miễn', '%', 'bằng']):
                        text_prices.append(line)
                    else:
                        non_price_desc.append(line)

                if text_prices:
                    prices = text_prices
                    description_lines = non_price_desc

                # If we have multiple consecutive price lines, they form the price array
                # (e.g., two text descriptions for two columns)

            # Clean up description - remove metadata like "Cước đảo chuyển..."
            clean_description_lines = []
            for line in description_lines:
                # Skip lines that are clearly metadata/notes/references
                skip_keywords = [
                    'cước đảo chuyển', 'ghi chú', 'lưu ý', 'chú ý',
                    'dưới đây tại', 'tại bảng', 'bảng', 'quay lại',
                    'theo quy định'
                ]
                if not any(keyword in line.lower() for keyword in skip_keywords):
                    clean_description_lines.append(line)

            description = ' '.join(clean_description_lines).strip()

            return {
                'num': row_num,
                'description': description,
                'prices': prices[:5],  # Usually 5 prices (3 dry + 2 cold)
                'next_idx': idx
            }

        # Pattern 2: Row number + description + prices on same line
        elif re.match(r'^\d+\s+.+', first_line):
            parts = first_line.split()
            row_num = parts[0]

            # Remove row number from line, then split text and prices
            rest_of_line = first_line[len(row_num):].strip()
            text_part, prices = self._split_text_and_prices(rest_of_line)

            # Post-processing: if no prices found but text contains "Thỏa thuận Thỏa thuận" etc,
            # split them as separate prices
            if not prices and text_part and 'Thỏa thuận' in text_part:
                # Separate description from prices
                # Pattern: "OOG nhóm 2 (**) Thỏa thuận Thỏa thuận" -> desc="OOG nhóm 2 (**)", prices=["Thỏa thuận", "Thỏa thuận"]
                parts_match = re.match(r'^(.+?)\s+(Thỏa thuận.*)$', text_part)
                if parts_match:
                    description_part = parts_match.group(1)
                    prices_part = parts_match.group(2)
                    count = prices_part.count('Thỏa thuận')
                    if count >= 2:
                        prices = ['Thỏa thuận'] * count
                        text_part = description_part
                else:
                    # Fallback: just count and extract
                    count = text_part.count('Thỏa thuận')
                    if count >= 2:
                        prices = ['Thỏa thuận'] * count
                        text_part = ''  # Clear description if we can't parse it

            description = text_part

            # Check for additional price line following
            idx = start_idx + 1
            additional_prices = []
            current_price_text = []  # Accumulate multi-line price text

            while idx < len(table_lines) and len(prices) < 5:
                next_line = table_lines[idx].strip()

                if not next_line:
                    idx += 1
                    continue

                # Stop if we hit next row, header, or section
                if re.match(r'^\d+\s*(\s|$)', next_line) or self._is_table_header_line(next_line) or self._is_section_heading(next_line):
                    # Finish accumulating current price if any
                    if current_price_text:
                        additional_prices.append(' '.join(current_price_text))
                        current_price_text = []
                    break

                # Check if this line is numeric prices
                if not any(char.isalpha() for char in next_line if char not in '& '):
                    # Finish accumulating current price if any
                    if current_price_text:
                        additional_prices.append(' '.join(current_price_text))
                        current_price_text = []

                    more_prices = self._extract_prices_from_line(next_line)
                    if more_prices and len(more_prices) >= 3:
                        prices.extend(more_prices)
                        idx += 1
                        continue
                    else:
                        # Not prices, stop here
                        break

                # Check if this line starts a new text-based price or continues one
                if any(keyword in next_line.lower() for keyword in ['tăng', 'thỏa thuận', 'miễn', '%', 'bằng', 'bằng tổng']):
                    # This line starts a new price
                    if current_price_text:
                        # Save previous price
                        additional_prices.append(' '.join(current_price_text))
                    current_price_text = [next_line]
                    idx += 1
                    continue
                else:
                    # Check if this might be a continuation of a text-based price
                    if current_price_text and len(next_line) < 40 and any(char.isalpha() for char in next_line):
                        # Likely continuation of price (like "hàng thông thường")
                        current_price_text.append(next_line)
                        idx += 1
                        continue
                    else:
                        # Regular text, stop collecting prices
                        if current_price_text:
                            additional_prices.append(' '.join(current_price_text))
                            current_price_text = []
                        break

            # Finish any remaining price text
            if current_price_text:
                additional_prices.append(' '.join(current_price_text))

            # Use text-based prices if no numeric prices were found
            if not prices and additional_prices:
                prices = additional_prices

            return {
                'num': row_num,
                'description': description,
                'prices': prices[:5],  # Keep only first 5 prices
                'next_idx': idx
            }

        return None

    def _parse_data_row_start(self, line: str) -> Dict:
        """Parse the start of a data row"""
        # Format: {num} {description} {maybe_prices}
        parts = line.split()

        if not parts:
            return {'num': '', 'description': '', 'prices': []}

        row_num = parts[0]
        remaining = ' '.join(parts[1:])

        # Try to separate description from prices
        # Prices are sequences of digits with dots (thousand separators)
        prices = self._extract_prices_from_line(remaining)
        description_part = remaining

        if prices:
            # Remove prices from description
            for price in prices:
                description_part = description_part.replace(price, '', 1)

        description = ' '.join(description_part.split()).strip()

        return {
            'num': row_num,
            'description': description,
            'prices': prices
        }

    def _extract_prices_from_line(self, line: str) -> List[str]:
        """Extract price values from a line"""
        # Prices are numbers with dot thousand separators
        # Pattern: digit + (dot + digits)* + digit
        # Examples: 497.000, 1.031.000, 143.000
        prices = re.findall(r'\d[\d.]*', line)

        # Filter out false positives (single digits, numbers without thousand separator)
        valid_prices = []
        for price in prices:
            # Valid price has at least 4 digits total or has a dot
            if len(price.replace('.', '')) >= 4 or '.' in price:
                valid_prices.append(price)

        return valid_prices

    def _split_text_and_prices(self, line: str) -> Tuple[str, List[str]]:
        """
        Split a mixed text-price line into description and prices.

        Examples:
        "Tàu/Sà lan  Bãi 461.160 677.160 1.015.200 664.200 972.000"
        -> ("Tàu/Sà lan  Bãi", ["461.160", "677.160", "1.015.200", "664.200", "972.000"])

        "Xe  Bãi 497.000 882.000 1.031.000 646.000 1.136.000"
        -> ("Xe  Bãi", ["497.000", "882.000", "1.031.000", "646.000", "1.136.000"])
        """
        # Find all prices in the line
        prices = self._extract_prices_from_line(line)

        if not prices:
            return (line.strip(), [])

        # Find the position of the first price
        first_price_match = re.search(r'\d[\d.]*', line)
        if not first_price_match:
            return (line.strip(), [])

        # Text is everything before the first price
        text_part = line[:first_price_match.start()].strip()

        return (text_part, prices)

    def _is_table_header_line(self, line: str) -> bool:
        """
        Check if line is a table header.

        Real headers have specific patterns like:
        - "Container khô Container lạnh" (TWO container types)
        - "TT Phương án làm hàng"
        - "Đơn vị tính: đồng/container"
        - Vietnamese arrow headers from preprocessing in section 1.1.4
        - "Tàu/ Sà lan ... Bãi" etc. (with Unicode arrows uf0f3)

        NOT just any line containing these keywords.
        """
        line_lower = line.lower()

        # Skip data rows
        if re.match(r'^\d+\s+', line):
            return False

        # Pattern: Preprocessed column headers from section 1.1.4 (start with "Từ")
        if line.startswith('Từ ') and ('bãi' in line_lower or 'xe' in line_lower or 'tàu' in line_lower):
            return True

        # Pattern: Original column header with arrow symbols (Tàu/Sà lan ↔ Bãi)
        if 'Tàu' in line or 'Sà lan' in line or 'Xe' in line:
            if any(arrow in line for arrow in ['↔', '→', '←', '\uf0f3']):
                return True

        # Specific header patterns to match
        # Pattern 1: "Container X Container Y" (must have TWO container types side by side)
        if re.search(r'container\s+(khô|lạnh|rỗng).*container\s+(khô|lạnh|rỗng)', line_lower):
            return True

        # Pattern 2: "TT Phương án" or similar column headers at START of line
        if re.search(r'^(tt|tên|loại|phương\s+án)\s+', line_lower):
            return True

        # Pattern 3: "Đơn vị tính:" or "Đơn vị trọng lượng" - unit indicators
        if re.search(r'đơn\s+vị\s+(tính|trọng|thời)', line_lower):
            return True

        # Pattern 4: Size specifications like "20' 40' 45'" (multiple sizes)
        sizes = re.findall(r"\d+[''ʼ\u2019]", line)
        if len(sizes) >= 3:  # Multiple sizes indicates header row
            return True

        # Pattern 5: Single size or continuation of size header (e.g., "40' &" or "45'")
        # Usually appears as a continuation of a multi-line header
        if re.match(r"^\s*\d+[''ʼ\u2019]\s*(&|,|\s|$)", line):
            return True

        return False

    def _is_table_data_line(self, line: str) -> bool:
        """Check if line contains table data (starts with row number)"""
        return bool(re.match(r'^\d+\s+', line))

    def _parse_table_row(self, line: str, headers: List[str]) -> Optional[Dict]:
        """
        Parse a table data row.

        Expected format: {row_num} {description} {price1} {price2} ...
        """
        # Split by whitespace
        parts = line.split()
        if not parts or not parts[0].isdigit():
            return None

        row_num = parts[0]
        remaining = ' '.join(parts[1:])

        # Try to separate description from prices
        # Prices are numeric values with optional thousand separators
        matches = list(re.finditer(r'\d[\d.]*\d{3}', remaining))

        if matches:
            # Everything before first price is description
            first_price_pos = matches[0].start()
            description = remaining[:first_price_pos].strip()
            prices_str = remaining[first_price_pos:].strip()

            # Extract individual prices
            prices = re.findall(r'\d[\d.]*', prices_str)

            return {
                'num': row_num,
                'description': description,
                'prices': {'Price': price for price in prices}
            }
        else:
            # No prices found, treat as description only
            return {
                'num': row_num,
                'description': remaining,
                'prices': {}
            }

    def _extract_price_columns(self, headers_str: str) -> List[str]:
        """Extract price column names from header string"""
        # Look for patterns like: 20' 40' 45' Container khô Container lạnh
        columns = []

        # Find all quoted sizes: 20', 40', 45'
        sizes = re.findall(r"(\d+[''ʼ\u2019])", headers_str)

        if sizes:
            # Group sizes by type (khô, lạnh)
            if 'khô' in headers_str.lower():
                for size in sizes[:3]:  # First 3 are usually dry
                    columns.append(f"Container khô {size}")
            if 'lạnh' in headers_str.lower():
                for size in sizes[3:6] if len(sizes) > 3 else sizes:  # Rest are cold
                    columns.append(f"Container lạnh {size}")

        if not columns:
            # Fallback to generic price columns
            columns = ['Price 1', 'Price 2', 'Price 3']

        return columns

    def _convert_markdown_tables(self, markdown_content: str) -> str:
        """
        Convert markdown tables (with | pipes) to bullet format.

        This is the original converter logic for markdown-formatted tables.
        """
        logger.info("Starting markdown table conversion")

        # Preprocessing: Move "Bảng XX" headings before their tables
        markdown_content = self._reorder_table_headings(markdown_content)

        lines = markdown_content.split('\n')
        result = []
        in_table = False
        current_table_rows = []
        skip_next = False
        last_heading = None

        for i, line in enumerate(lines):
            # Skip watermark and page markers
            if '[Image on page' in line or '<!-- Page' in line:
                continue

            # Skip page footer/separator lines (extracted as text from PDF)
            if 'Biểu giá dịch vụ tại cảng Tân Cảng' in line and 'từ ngày' in line:
                continue

            # Skip empty lines unless they're meaningful
            if not line.strip():
                if result and result[-1]:  # Only add if previous line wasn't empty
                    result.append('')
                continue

            # Handle table rows
            if line.strip().startswith('|'):
                if not in_table:
                    in_table = True
                    current_table_rows = []

                current_table_rows.append(line)
                skip_next = True
                continue

            # Handle multi-line table cells (lines that don't start with | but follow table rows)
            # These are continuation lines of table cell content
            if in_table and not line.strip().startswith('|'):
                # Check if this is a table continuation (has pipe | characters)
                # or just regular content after the table
                if '|' in line:
                    # Likely a continuation of the previous table cell
                    # Append to the last table row to preserve cell content
                    if current_table_rows:
                        current_table_rows[-1] += ' ' + line.strip()
                    continue
                else:
                    # No pipe chars - this is the end of the table
                    if current_table_rows:
                        table_bullets = self._parse_markdown_table(current_table_rows, last_heading)
                        result.extend(table_bullets)
                        current_table_rows = []
                    in_table = False

            if skip_next:
                skip_next = False
                continue

            # Handle headings
            if line.strip().startswith('#'):
                heading_text = line.strip().lstrip('#').strip()

                # "Bảng XX" headings should be converted to plain text, not styled headings
                # This ensures table labels appear inline with content, not as separate sections
                if heading_text.startswith('Bảng'):
                    # Add as plain text with underline
                    result.append(heading_text)
                    result.append('━' * min(len(heading_text) + 2, 80))
                    result.append('')
                else:
                    heading_result = self._convert_heading(line)
                    result.extend(heading_result)
                    # Extract heading for table context
                    last_heading = heading_text
                continue

            # Handle notes/remarks (Ghi chú)
            if line.strip().lower().startswith('ghi chú'):
                result.append(f"┃ ⓘ {line.strip()}")
                continue

            # Handle existing bullets
            if line.strip().startswith(('-', '*', '+')):
                formatted = self._format_bullet_line(line)
                result.append(formatted)
                continue
            elif line.strip().startswith('•'):
                # Already a bullet, keep as-is
                result.append(line.strip())
                continue

            # Handle normal text - add as bullet if not empty
            if line.strip():
                # Skip metadata/signature lines
                skip_keywords = [
                    'người in:', 'người ký:', 'thời gian', 'thủ trưởng',
                    'ban chỉ huy', 'ct/tgđ', 'email', '.vn', 'điện thoại',
                    'ngày in:', 'fax:', 'địa chỉ:', 'tổng công ty'
                ]
                text_lower = line.strip().lower()
                if any(keyword in text_lower for keyword in skip_keywords):
                    continue

                # Check if this looks like a note/remark
                text = line.strip()
                if any(keyword in text.lower() for keyword in ['ghi chú', 'chú ý', 'lưu ý', 'cụ thể']):
                    result.append(f"ⓘ {text}")
                else:
                    result.append(f"• {text}")

        # Handle last table if exists
        if in_table and current_table_rows:
            table_bullets = self._parse_markdown_table(current_table_rows, last_heading)
            result.extend(table_bullets)

        output = '\n'.join(result)
        logger.info("Markdown table conversion completed")
        return output

    def _convert_heading(self, heading_line: str) -> List[str]:
        """Convert markdown heading to bullet format with Vietnamese styling"""
        stripped = heading_line.strip()
        level = len(stripped) - len(stripped.lstrip('#'))

        title = stripped.lstrip('#').strip()

        # Convert arrows in heading
        title = self._convert_arrow(title)

        result = []

        # Level 1 headings: Main document title with full underline
        if level == 1:
            result.append(title)
            result.append('━' * 80)
            result.append('')  # Add spacing after header
        # Level 2 headings: Table/section title
        elif level == 2:
            result.append('')
            result.append(title)
            result.append('━' * min(len(title) + 2, 80))
            result.append('')
        # Level 3 headings: Main section/table title with underline
        elif level == 3:
            result.append(title)
            result.append('━' * min(len(title), 80))
        # Level 4+ headings: Sub-bullets
        else:
            indent = "  " * (level - 3) if level > 3 else ""
            result.append(f"{indent}• {title}")

        return result

    def _format_bullet_line(self, line: str) -> str:
        """Format existing bullet line"""
        stripped = line.strip()
        # Convert to standard bullet if it's another style
        if stripped.startswith('*'):
            return '•' + stripped[1:]
        elif stripped.startswith('+'):
            return '•' + stripped[1:]
        return line

    def _convert_arrow(self, text: str) -> str:
        """
        Convert arrows to natural Vietnamese sentences.

        Examples:
        - "Xe ↔ Bãi" → "Xe xuống bãi hoặc từ bãi lên xe"
        - "Tàu/Sà lan → Bãi" → "Tàu hoặc sà lan đến bãi"
        - "Bãi ← Tàu/Sà lan" → "Từ bãi lên tàu hoặc sà lan"
        """

        # Two-way: Xe ↔ Bãi
        if '↔' in text or '<->' in text:
            # Normalize the arrow
            text = text.replace('↔', '<->').replace('<->', '<->')

            parts = [p.strip() for p in text.split('<->')]
            if len(parts) == 2:
                obj1 = parts[0]
                obj2 = parts[1]

                if 'Xe' in obj1:
                    return f"Xe xuống bãi hoặc từ bãi lên xe"
                elif 'Tàu' in obj1 or 'Sà lan' in obj1:
                    return f"Tàu hoặc sà lan đến bãi hoặc từ bãi lên tàu hoặc sà lan"

        # One-way down: → Bãi
        if '→' in text or '->' in text:
            text = text.replace('→', '->')
            parts = [p.strip() for p in text.split('->')]

            if len(parts) == 2:
                obj1 = parts[0]
                obj2 = parts[1]

                if 'Xe' in obj1 and 'Bãi' in obj2:
                    return "Xe xuống bãi"
                elif ('Tàu' in obj1 or 'Sà lan' in obj1) and 'Bãi' in obj2:
                    return "Tàu hoặc sà lan đến bãi"

        # One-way up: ← Xe
        if '←' in text or '<-' in text:
            text = text.replace('←', '<-')
            parts = [p.strip() for p in text.split('<-')]

            if len(parts) == 2:
                obj1 = parts[0]
                obj2 = parts[1]

                if 'Xe' in obj2 and 'Bãi' in obj1:
                    return "Từ bãi lên xe"
                elif ('Tàu' in obj2 or 'Sà lan' in obj2) and 'Bãi' in obj1:
                    return "Từ bãi lên tàu hoặc sà lan"

        return text

    def _parse_markdown_table(self, table_rows: List[str], context_heading: Optional[str] = None) -> List[str]:
        """
        Parse markdown table to bullet format with Vietnamese document styling.

        Handles multi-row headers with container sizes (20', 40', 45', etc.)

        Structure:
        Row 0: | Phương án | Container khô |  |  | Container lạnh |  |
        Row 1: | --- | --- | --- | --- | --- | --- | (separator)
        Row 2: |  | 20' | 40' | 45' | 20' | 40' & 45' | (sub-headers)
        Row 3+: | data | data | data | ... |
        """

        if not table_rows or len(table_rows) < 2:
            return []

        result = []

        # Detect if this is a multi-row header table
        header_row = table_rows[0]
        separator_idx = None
        for idx in range(1, min(4, len(table_rows))):  # Look for separator in first 4 rows
            if '---' in table_rows[idx]:
                separator_idx = idx
                logger.debug(f"Found separator at index {separator_idx}")
                break

        # Check if row after separator has sub-headers
        has_multi_row_header = False
        sub_headers = None
        data_start_idx = 2

        if separator_idx is not None and len(table_rows) > separator_idx + 1:
            potential_sub_header = table_rows[separator_idx + 1]

            # Check for container sizes OR other sub-headers
            # Match patterns like: 20', 40', 45' (container sizes) or "Tàu/ Sà lan" (location indicators)
            has_container_size = bool(re.search(r"\d+[''ʼ\u2019]", potential_sub_header))
            has_location_header = bool(re.search(r"[Tt]àu|[Ss]à lan|[Bb]ãi|[Xx]e", potential_sub_header))
            has_any_text_in_pipes = len([h for h in potential_sub_header.split('|')[1:-1] if h.strip()]) > 0

            if has_container_size or has_location_header or (has_any_text_in_pipes and separator_idx == 1):
                has_multi_row_header = True
                sub_headers_raw = [h.strip() for h in potential_sub_header.split('|')[1:-1]]
                sub_headers = [self._clean_header(h) if h.strip() else '' for h in sub_headers_raw]
                data_start_idx = separator_idx + 2

        # Parse main headers
        headers = [h.strip() for h in header_row.split('|')[1:-1]]
        headers = [self._clean_header(h) for h in headers]

        # Determine table type
        has_tt = 'TT' in (headers[0] if headers else '')
        has_loai_container = any('loại' in h.lower() or 'container' in h.lower() for i, h in enumerate(headers) if i == 1)
        has_phuong_an = any('phương' in h.lower() or 'phương án' in h.lower() for h in headers)

        # Build combined headers if multi-row
        if has_multi_row_header and sub_headers:
            combined_headers = []
            current_main_header = ""

            for i, main_header in enumerate(headers):
                sub_header = sub_headers[i] if i < len(sub_headers) else ""

                # Track the current main category (Container khô, Container lạnh, etc.)
                if main_header and main_header.strip():
                    current_main_header = main_header

                # Build combined header
                if sub_header and sub_header.strip():
                    # Has sub-header (like 20', 40', 45')
                    if current_main_header:
                        combined = f"{current_main_header} {sub_header}"
                    else:
                        combined = sub_header
                    combined_headers.append(combined)
                elif main_header and main_header.strip():
                    # Main header only
                    combined_headers.append(main_header)
                else:
                    # Empty - skip
                    combined_headers.append("")

            headers = combined_headers

        # Get data rows
        data_rows = table_rows[data_start_idx:] if data_start_idx < len(table_rows) else []

        # Parse data rows
        for row_idx, row in enumerate(data_rows):
            # Skip separator rows
            if '---' in row:
                continue

            cells = [c.strip() for c in row.split('|')[1:-1]]

            if len(cells) < 2 or not any(cells):  # Skip empty rows
                continue

            # Detect ghi chú (note) rows - typically have empty first cells but content in later columns
            # Example: |  |  | Cước đảo chuyển ... |  |  |
            empty_cell_count = sum(1 for i in range(min(2, len(cells))) if not cells[i])
            has_content = any(cells[i] for i in range(2, len(cells))) if len(cells) > 2 else False
            is_note_row = (empty_cell_count == 2 and has_content and
                          any(keyword in ''.join(cells).lower() for keyword in
                              ['cước', 'ghi chú', 'chú ý', 'lưu ý', 'quy định', 'được']))

            if is_note_row:
                # Handle as note row - find the text content and format as note
                note_text = ' '.join(c for c in cells if c.strip())
                result.append(f"ⓘ {note_text}")
                result.append('')
                continue

            # Get action/description from appropriate column
            if has_tt and has_loai_container and has_phuong_an:
                # Format: TT | Loại container | Phương án | Prices...
                loai_container = cells[1] if len(cells) > 1 else ''
                action_idx = 2  # Start from Phương án column
                tt_num = cells[0] if len(cells) > 0 else ''
            elif has_tt and has_phuong_an:
                # Format: TT | Phương án | Prices...
                loai_container = ''
                action_idx = 1
                tt_num = cells[0] if len(cells) > 0 else ''
            elif has_loai_container and has_phuong_an:
                # Format: Loại container | Phương án | Prices...
                loai_container = cells[0] if len(cells) > 0 else ''
                action_idx = 1
                tt_num = ''
            elif has_phuong_an:
                loai_container = ''
                action_idx = 0
                tt_num = ''
            else:
                loai_container = ''
                action_idx = 0
                tt_num = ''

            # Get the main action value
            action = cells[action_idx] if action_idx < len(cells) else ''

            # Clean up action text (remove watermark artifacts)
            action = self._clean_cell_content(action)
            loai_container = self._clean_cell_content(loai_container)

            if action or loai_container:
                # Convert arrows in action
                action = self._convert_arrow(action)
                loai_container = self._convert_arrow(loai_container)

                # Build the title: include loại container if available
                if loai_container and loai_container.strip():
                    if tt_num and tt_num.strip():
                        title = f"{tt_num}: {loai_container}"
                    else:
                        title = loai_container
                else:
                    title = action if action else 'Phương án'
                    action = ''  # Don't duplicate the action

                # Format as boxed phương án (option/solution)
                result.append(f"┃ PHƯƠNG ÁN {title}" if title and not title.startswith('PHƯƠNG ÁN') else f"┃ {title if title.startswith('PHƯƠNG ÁN') else 'PHƯƠNG ÁN ' + title}")
                result.append('┣' + '━' * 70)

                # If we separated loai_container, add action as first item
                if loai_container and loai_container.strip() and action and action.strip():
                    result.append(f"┃ • Phương án làm hàng    → {action}")

                # Add prices as sub-bullets with proper alignment
                prices_added = False
                if loai_container and loai_container.strip():
                    # When we have loai_container, start from action_idx (which includes both action and prices)
                    start_idx = action_idx + 1
                else:
                    # Normal case: all values after action
                    start_idx = action_idx + 1

                for i in range(start_idx, len(cells)):
                    if i < len(headers) and cells[i] and cells[i].strip():
                        header = headers[i]
                        price = cells[i].strip()

                        # Clean price
                        price = self._clean_cell_content(price)

                        # Format: "20' khô" → "497.000"
                        # Use ┃ prefix to match sample format
                        result.append(f"┃ • {header:25} → {price}")
                        prices_added = True

                # Add spacing between options
                if prices_added or (loai_container and loai_container.strip()):
                    result.append('')

        return result

    def _clean_header(self, header: str) -> str:
        """Clean header text from markdown artifacts"""
        # Remove watermark artifacts
        header = re.sub(r'[a-z]\n[a-z]|[A-Z]\s+[a-z]', '', header)
        header = re.sub(r'[\n\r]+', ' ', header)
        header = ' '.join(header.split())  # Normalize whitespace
        return header.strip()

    def _clean_cell_content(self, cell: str) -> str:
        """Clean cell content from PDF extraction artifacts"""
        # Remove watermark text artifacts (Vietnamese char patterns)
        # Pattern: single letters with newlines, PDF garbage
        cell = re.sub(r'[a-z]\n[a-z]', '', cell)
        cell = re.sub(r'[A-Z]\s+[a-z]\s+[A-Z]', '', cell)
        cell = re.sub(r'[\n\r]+', ' ', cell)
        cell = ' '.join(cell.split())  # Normalize whitespace

        # Remove common watermark patterns
        patterns = [
            r'in\s*:\s*$',
            r'ờ\s*i\s*$',
            r'ừ.*ng\s*$',
            r'ịn\s*r\s*T\s*$',
            r'@\s*k\s*',
        ]
        for pattern in patterns:
            cell = re.sub(pattern, '', cell, flags=re.IGNORECASE)

        return cell.strip()
