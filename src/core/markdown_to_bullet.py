"""
Markdown to Bullet List Converter

Converts markdown content to bullet format with natural language arrow conversion.
Handles tables, headings, and special cases for port pricing documents.

Formats output to match Vietnamese document standards with proper boxing and alignment.
"""

import re
from typing import List, Dict, Tuple, Optional
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

    def convert(self, markdown_content: str) -> str:
        """
        Convert markdown to bullet list format.

        Args:
            markdown_content: Raw markdown text

        Returns:
            Formatted bullet list text with proper Vietnamese document styling
        """
        logger.info("Starting markdown to bullet conversion")

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

            # End of table
            if in_table and not line.strip().startswith('|'):
                if current_table_rows:
                    table_bullets = self._parse_table(current_table_rows, last_heading)
                    result.extend(table_bullets)
                    current_table_rows = []
                in_table = False

            if skip_next:
                skip_next = False
                continue

            # Handle headings
            if line.strip().startswith('#'):
                heading_result = self._convert_heading(line)
                result.extend(heading_result)
                # Extract heading for table context
                last_heading = line.strip().lstrip('#').strip()
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
            table_bullets = self._parse_table(current_table_rows, last_heading)
            result.extend(table_bullets)

        output = '\n'.join(result)
        logger.info("Markdown to bullet conversion completed")
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

    def _parse_table(self, table_rows: List[str], context_heading: Optional[str] = None) -> List[str]:
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
