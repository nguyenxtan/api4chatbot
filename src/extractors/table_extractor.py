"""
Table extraction from markdown and text.
"""
import re
from typing import List, Optional, Dict, Tuple
from loguru import logger

from src.models import ExtractedTableData


class TableExtractor:
    """Extract and parse tables from markdown text."""

    def extract_all_tables(self, markdown_text: str) -> List[ExtractedTableData]:
        """
        Extract all tables from markdown text.

        Args:
            markdown_text: Markdown formatted text

        Returns:
            List of extracted tables
        """
        tables = []
        lines = markdown_text.split("\n")

        i = 0
        while i < len(lines):
            # Check if line starts a table
            if self._is_table_row(lines[i]):
                table, last_line = self._extract_table_from_position(lines, i)
                if table:
                    tables.append(table)
                i = last_line + 1
            else:
                i += 1

        logger.info(f"Extracted {len(tables)} tables")
        return tables

    def extract_table_with_context(
        self,
        markdown_text: str,
        context_lines_before: int = 3,
        context_lines_after: int = 1
    ) -> List[Dict[str, any]]:
        """
        Extract tables with surrounding context.

        Args:
            markdown_text: Markdown text
            context_lines_before: Lines to include before table
            context_lines_after: Lines to include after table

        Returns:
            List of tables with context
        """
        results = []
        lines = markdown_text.split("\n")

        i = 0
        while i < len(lines):
            if self._is_table_row(lines[i]):
                table, last_line = self._extract_table_from_position(lines, i)
                if table:
                    # Extract context
                    start_context = max(0, i - context_lines_before)
                    end_context = min(len(lines), last_line + 1 + context_lines_after)

                    context_before = "\n".join(lines[start_context:i])
                    context_after = "\n".join(lines[last_line + 1:end_context])

                    # Look for caption in context before
                    caption = self._find_caption(context_before)
                    if caption:
                        table.caption = caption

                    results.append({
                        "table": table,
                        "context_before": context_before,
                        "context_after": context_after,
                        "start_line": i,
                        "end_line": last_line,
                    })
                i = last_line + 1
            else:
                i += 1

        return results

    def _is_table_row(self, line: str) -> bool:
        """Check if line is a markdown table row."""
        stripped = line.strip()
        if not stripped:
            return False

        # Markdown table rows start and end with |
        if stripped.startswith("|") and stripped.endswith("|"):
            # Must have at least 2 cells
            cells = stripped.split("|")
            return len(cells) >= 3  # At least | cell1 | cell2 |

        return False

    def _is_separator_row(self, line: str) -> bool:
        """Check if line is a markdown table separator (|---|---|)."""
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            return False

        # Remove outer pipes
        content = stripped[1:-1]
        cells = content.split("|")

        # Each cell should be dashes and optional colons
        for cell in cells:
            cell = cell.strip()
            if not re.match(r"^:?-+:?$", cell):
                return False

        return True

    def _extract_table_from_position(
        self,
        lines: List[str],
        start: int
    ) -> Tuple[Optional[ExtractedTableData], int]:
        """
        Extract a table starting at given position.

        Args:
            lines: All lines
            start: Starting line index

        Returns:
            (ExtractedTableData, last_line_index) or (None, start)
        """
        if not self._is_table_row(lines[start]):
            return None, start

        # Find table boundaries
        end = start
        while end < len(lines) and self._is_table_row(lines[end]):
            end += 1
        end -= 1  # Last table row

        if end <= start:
            return None, start

        # Parse table rows
        table_lines = lines[start:end + 1]

        # Check for header separator
        has_header = False
        header_row = None
        data_rows = []

        if len(table_lines) >= 2 and self._is_separator_row(table_lines[1]):
            has_header = True
            header_row = self._parse_table_row(table_lines[0])
            data_rows = [self._parse_table_row(line) for line in table_lines[2:]]
        else:
            # No header separator, treat first row as header
            header_row = self._parse_table_row(table_lines[0])
            data_rows = [self._parse_table_row(line) for line in table_lines[1:]]

        if not header_row:
            return None, start

        # Create ExtractedTableData
        table_data = ExtractedTableData(
            headers=header_row,
            rows=data_rows,
            row_count=len(data_rows),
            column_count=len(header_row),
            table_id=None,  # Will be set from context
            caption=None,   # Will be set from context
        )

        return table_data, end

    def _parse_table_row(self, line: str) -> List[str]:
        """Parse a table row into cells."""
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            return []

        # Remove outer pipes
        content = stripped[1:-1]

        # Split by pipe
        cells = content.split("|")

        # Strip whitespace from each cell
        return [cell.strip() for cell in cells]

    def _find_caption(self, context: str) -> Optional[str]:
        """
        Find table caption in context text.

        Args:
            context: Text before table

        Returns:
            Caption text if found
        """
        # Look for patterns like "Bảng 01: Caption text"
        caption_patterns = [
            r"Bảng\s+(?:\d+|[IVX]+|[\d-]+):\s*(.+)",
            r"Bảng\s+(?:\d+|[IVX]+|[\d-]+)\s*[:\-]\s*(.+)",
            r"Table\s+\d+:\s*(.+)",
        ]

        lines = context.strip().split("\n")
        # Check last few lines (caption usually right before table)
        for line in reversed(lines[-3:]):
            for pattern in caption_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return None

    def extract_table_id(self, context: str) -> Optional[str]:
        """
        Extract table ID from context.

        Args:
            context: Text containing table reference

        Returns:
            Table ID (e.g., "Bảng 01", "Bảng IV")
        """
        patterns = [
            r"(Bảng\s+(?:\d+|[IVX]+|[\d-]+(?:-[A-Z]+)?))",
        ]

        for pattern in patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def identify_table_type(self, table: ExtractedTableData) -> str:
        """
        Identify the type of table based on headers and content.

        Args:
            table: Extracted table data

        Returns:
            Table type ("pricing", "comparison", "data", "schedule", "unknown")
        """
        headers = [h.lower() for h in table.headers]

        # Pricing table indicators
        pricing_keywords = ["giá", "cước", "phí", "vnd", "usd", "eur", "cost", "price"]
        if any(kw in " ".join(headers) for kw in pricing_keywords):
            return "pricing"

        # Schedule/timeline table
        schedule_keywords = ["ngày", "tháng", "thời gian", "date", "time"]
        if any(kw in " ".join(headers) for kw in schedule_keywords):
            return "schedule"

        # Comparison table
        comparison_keywords = ["so sánh", "trước", "sau", "before", "after"]
        if any(kw in " ".join(headers) for kw in comparison_keywords):
            return "comparison"

        # Data/metrics table
        data_keywords = ["số liệu", "thống kê", "tỷ lệ", "data", "statistics"]
        if any(kw in " ".join(headers) for kw in data_keywords):
            return "data"

        return "unknown"

    def extract_container_type_columns(self, table: ExtractedTableData) -> Dict[str, int]:
        """
        Identify columns containing container types.

        Args:
            table: Table data

        Returns:
            Dict mapping container type to column index
        """
        container_pattern = r"(20'|40'|45')(?:\s*(DC|GP|HC|OT|FR))?"
        result = {}

        for idx, header in enumerate(table.headers):
            match = re.search(container_pattern, header)
            if match:
                container_type = match.group(0)
                result[container_type] = idx

        return result

    def group_rows_by_criteria(
        self,
        table: ExtractedTableData,
        group_column_index: int
    ) -> Dict[str, List[List[str]]]:
        """
        Group table rows by a specific column value.

        Args:
            table: Table data
            group_column_index: Column index to group by

        Returns:
            Dict mapping group key to rows
        """
        groups: Dict[str, List[List[str]]] = {}

        for row in table.rows:
            if group_column_index >= len(row):
                continue

            key = row[group_column_index].strip()
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        return groups

    def extract_numeric_values(self, table: ExtractedTableData) -> List[Tuple[int, int, float]]:
        """
        Extract all numeric values from table with positions.

        Args:
            table: Table data

        Returns:
            List of (row_idx, col_idx, value)
        """
        results = []

        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row):
                # Try to extract number
                # Remove common formatting (commas, spaces)
                cleaned = cell.replace(",", "").replace(" ", "").replace(".", "")
                try:
                    value = float(cleaned)
                    results.append((row_idx, col_idx, value))
                except ValueError:
                    # Not a number
                    pass

        return results

    def convert_table_to_dict(self, table: ExtractedTableData) -> List[Dict[str, str]]:
        """
        Convert table to list of dictionaries (one per row).

        Args:
            table: Table data

        Returns:
            List of row dictionaries
        """
        result = []

        for row in table.rows:
            row_dict = {}
            for idx, header in enumerate(table.headers):
                if idx < len(row):
                    row_dict[header] = row[idx]
                else:
                    row_dict[header] = ""
            result.append(row_dict)

        return result

    def find_table_by_id(
        self,
        markdown_text: str,
        table_id: str
    ) -> Optional[ExtractedTableData]:
        """
        Find a specific table by ID.

        Args:
            markdown_text: Full markdown text
            table_id: Table identifier (e.g., "Bảng 01")

        Returns:
            Table data if found
        """
        tables_with_context = self.extract_table_with_context(markdown_text)

        for item in tables_with_context:
            # Look for table ID in context
            context = item["context_before"] + "\n" + item.get("caption", "")
            if table_id.lower() in context.lower():
                return item["table"]

        return None
