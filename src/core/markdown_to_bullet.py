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

        # Check if input is N8N JSON format (has tables without markdown pipes)
        if self._is_text_based_table_format(input_content):
            logger.info("Detected text-based table format (N8N extraction)")
            return self._convert_text_based_tables(input_content)
        else:
            logger.info("Detected markdown table format")
            return self._convert_markdown_tables(input_content)

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

            # Regular content (descriptions, notes, etc.)
            if line.strip():
                # Skip metadata/signature lines
                if self._should_skip_line(line):
                    i += 1
                    continue

                # Add as bullet point
                if line.strip().startswith(('-', '*', '•')):
                    result.append(line.strip())
                else:
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
        table_header = first_line

        result.append(table_header)
        result.append('━' * 80)
        result.append('')

        # Parse table structure: identify headers and data rows
        headers_tuple = self._extract_table_headers(table_lines)
        col_names = self._build_column_names(headers_tuple)

        # Parse rows - more sophisticated handling of multi-line rows
        rows_data = self._extract_table_rows(table_lines)

        # Format as bullets
        for row_idx, row_data in enumerate(rows_data):
            # Include row if it has either description or prices
            description = row_data.get('description', '')
            prices = row_data.get('prices', [])

            if description or prices:
                row_num = row_data['num']

                # Format: PHƯƠNG ÁN {num}: {description}
                result.append(f"┃ PHƯƠNG ÁN {row_num}: {description}")
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

        return result

    def _extract_table_headers(self, table_lines: List[str]) -> Tuple[str, str]:
        """
        Extract column headers from table lines.
        Returns (type_headers, size_headers) like ("Container khô Container lạnh", "20' 40' 45' 20' 40' & 45'")
        """
        type_header = ""
        size_header = ""

        for line in table_lines[1:6]:  # Look in first 5 lines after table title
            line = line.strip()
            if not line:
                continue

            # Skip data rows
            if re.match(r'^\d+\s+', line):
                continue

            # Check if this is the size line (contains multiple size patterns)
            if re.search(r"\d+[''ʼ\u2019]", line):
                size_header = line
            # Check if this is the type line (contains khô or lạnh)
            elif 'khô' in line.lower() or 'lạnh' in line.lower():
                type_header = line

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

        Handles the case where row data spans multiple lines:
        1 Xe Bãi 497.000 882.000 1.031.000 646.000 1.136.000
        2
        Hạ container ở tầng
        trên xuống đất phục vụ
        kiểm hoá.
        298.000 528.000 627.000 596.000 1.018.000
        """
        rows = []
        i = 1  # Skip first line (table title)

        while i < len(table_lines):
            line = table_lines[i].strip()

            if not line:
                i += 1
                continue

            # Skip header lines (these have multiple words/keywords but no prices starting)
            if self._is_table_header_line(line) and not re.match(r'^\d+\s*$', line):
                i += 1
                continue

            # Check if this is a data row
            # Pattern 1: Single digit (row number only): "1", "2", "3", etc.
            # Pattern 2: Digit + description: "1 Xe Bãi 497..."
            is_data_row = re.match(r'^\d+(\s|$)', line)

            if is_data_row:
                # Parse the row - could be single or multi-line
                row_data = self._parse_table_row_sequence(table_lines, i)
                if row_data:
                    rows.append(row_data)
                    i = row_data.get('next_idx', i + 1)
                else:
                    i += 1
            else:
                i += 1

        return rows

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

            # Next line(s) are description, last line has prices
            description_lines = []
            prices = []
            idx = start_idx + 1
            last_line_before_next_row = None

            # Collect all lines until next row
            content_lines = []
            while idx < len(table_lines):
                curr_line = table_lines[idx].strip()

                if not curr_line:
                    idx += 1
                    continue

                # Check if this is next row (single digit or header)
                if re.match(r'^\d+\s*$', curr_line) or self._is_table_header_line(curr_line):
                    break

                content_lines.append(curr_line)
                idx += 1

            # Last content line should have prices
            if content_lines:
                last_line = content_lines[-1]
                last_prices = self._extract_prices_from_line(last_line)

                if last_prices and len(last_prices) >= 4:
                    # Last line has prices
                    prices = last_prices
                    description_lines = content_lines[:-1]
                else:
                    # No prices in last line, treat all as description
                    description_lines = content_lines

            description = ' '.join(description_lines).strip()
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

            # Extract prices from the line
            prices = self._extract_prices_from_line(first_line)

            # Everything else is description
            desc_part = first_line[len(parts[0]):].strip()
            for price in prices:
                desc_part = desc_part.replace(price, '', 1)

            description = ' '.join(desc_part.split()).strip()

            # Check for additional price line following
            idx = start_idx + 1
            if idx < len(table_lines):
                next_line = table_lines[idx].strip()

                # Only collect additional prices if the next line is ONLY prices
                if next_line and not any(char.isalpha() for char in next_line if char not in '& '):
                    more_prices = self._extract_prices_from_line(next_line)
                    if more_prices and len(more_prices) >= 3:
                        prices.extend(more_prices)
                        idx += 1

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

    def _is_table_header_line(self, line: str) -> bool:
        """
        Check if line is a table header.

        Real headers have specific patterns like:
        - "Container khô Container lạnh"
        - "TT Phương án làm hàng"
        - "Đơn vị tính: đồng/container"

        NOT just any line containing these keywords.
        """
        line_lower = line.lower()

        # Skip data rows
        if re.match(r'^\d+\s+', line):
            return False

        # Specific header patterns to match
        # Pattern 1: "Container X Container Y"
        if re.search(r'container\s+(khô|lạnh|rỗng).*container', line_lower):
            return True

        # Pattern 2: "TT Phương án" or similar column headers
        if re.search(r'^(tt|tên|loại|phương\s+án)', line_lower):
            return True

        # Pattern 3: Has multiple header-like words in sequence
        # Like "Đơn vị tính: ..." or "Đơn vị trọng lượng"
        if re.search(r'đơn\s+vị|thời\s+gian|phương\s+án', line_lower):
            return True

        # Pattern 4: Size specifications like "20' 40' 45'"
        if re.search(r'\d+[''ʼ\u2019]', line):
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

        # Check if row after separator has container sizes
        has_multi_row_header = False
        sub_headers = None
        data_start_idx = 2

        if separator_idx is not None and len(table_rows) > separator_idx + 1:
            potential_sub_header = table_rows[separator_idx + 1]

            # Check for container sizes using regex (handles both ' and ' quotes)
            # Match patterns like: 20', 40', 45', 20', 40', 45' (with Unicode smart quote U+2019)
            has_container_size = bool(re.search(r"\d+[''ʼ\u2019]", potential_sub_header))

            if has_container_size:
                has_multi_row_header = True
                sub_headers_raw = [h.strip() for h in potential_sub_header.split('|')[1:-1]]
                sub_headers = [self._clean_header(h) if h.strip() else '' for h in sub_headers_raw]
                data_start_idx = separator_idx + 2

        # Parse main headers
        headers = [h.strip() for h in header_row.split('|')[1:-1]]
        headers = [self._clean_header(h) for h in headers]

        # Determine table type
        has_tt = 'TT' in (headers[0] if headers else '')
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

            # Get action/description from appropriate column
            if has_tt and has_phuong_an:
                # Format: TT | Phương án | Prices...
                action_idx = 1
            elif has_phuong_an:
                action_idx = 0
            else:
                action_idx = 0

            action = cells[action_idx] if action_idx < len(cells) else ''

            # Clean up action text (remove watermark artifacts)
            action = self._clean_cell_content(action)

            if action:
                # Convert arrows in action
                action = self._convert_arrow(action)

                # Get actual row number from TT column if exists
                if has_tt and len(cells) > 0:
                    try:
                        row_num = cells[0].strip()
                    except:
                        row_num = row_idx + 1
                else:
                    row_num = row_idx + 1

                # Format as boxed phương án (option/solution)
                result.append(f"┃ PHƯƠNG ÁN {row_num}: {action}")
                result.append('┣' + '━' * 70)

                # Add prices as sub-bullets with proper alignment
                prices_added = False
                for i in range(action_idx + 1, len(cells)):
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
                if prices_added:
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
