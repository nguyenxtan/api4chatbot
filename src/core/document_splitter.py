"""
Document splitter for extracting and splitting tables from markdown content.
Splits tables by TT (Thứ tự/Row number) threshold.
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class DocumentSplitter:
    """Split markdown document into table chunks with hierarchy preservation."""
    
    # Regex patterns
    TABLE_HEADER_PATTERN = re.compile(r'###\s+Bảng\s+(\d+[a-z]*)', re.IGNORECASE)
    HIERARCHY_PATTERNS = {
        'muc_chinh': re.compile(r'^([IVX]+\.|[A-Z]\.)\s+(.+)$'),  # I., II., A., B.
        'muc_cap_1': re.compile(r'^(1\.)\s+(.+)$'),
        'muc_cap_2': re.compile(r'^(1\.1\.)\s+(.+)$'),
        'muc_cap_3': re.compile(r'^(1\.1\.1\.)\s+(.+)$'),
    }
    
    TT_THRESHOLD = 5  # Split if TT >= 5
    ROWS_PER_PART = 5  # Max rows per part when splitting
    
    def __init__(self):
        self.current_hierarchy = {}
        self.tables = []
    
    def parse_markdown(self, markdown_text: str) -> List[Dict]:
        """
        Parse markdown content and extract tables with hierarchy.
        
        Args:
            markdown_text: Markdown content string
            
        Returns:
            List of table chunks with metadata
        """
        lines = markdown_text.split('\n')
        self.current_hierarchy = {}
        self.tables = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Update hierarchy from ### headings
            if line.startswith('###'):
                self._update_hierarchy(line)
            
            # Detect table header (### Bảng XX)
            match = self.TABLE_HEADER_PATTERN.search(line)
            if match:
                table_name = f"Bảng {match.group(1)}"
                i = self._extract_table(lines, i, table_name)
                continue
            
            i += 1
        
        return self.tables
    
    def _update_hierarchy(self, line: str):
        """Update current hierarchy from ### heading."""
        text = line.replace('###', '').strip()
        
        if not text or len(text) > 250:
            return
        
        # Check which hierarchy level this belongs to
        for level, pattern in self.HIERARCHY_PATTERNS.items():
            match = pattern.match(text)
            if match:
                self.current_hierarchy[level] = text
                # Clear lower levels when updating higher level
                if level == 'muc_chinh':
                    self.current_hierarchy.pop('muc_cap_1', None)
                    self.current_hierarchy.pop('muc_cap_2', None)
                    self.current_hierarchy.pop('muc_cap_3', None)
                elif level == 'muc_cap_1':
                    self.current_hierarchy.pop('muc_cap_2', None)
                    self.current_hierarchy.pop('muc_cap_3', None)
                elif level == 'muc_cap_2':
                    self.current_hierarchy.pop('muc_cap_3', None)
                break
    
    def _extract_table(self, lines: List[str], start_idx: int, table_name: str) -> int:
        """
        Extract table starting from start_idx.
        
        Returns:
            Index after table content
        """
        i = start_idx + 1
        
        # Find markdown table start (| ... |)
        table_start = None
        while i < len(lines) and table_start is None:
            if lines[i].strip().startswith('|'):
                table_start = i
                break
            i += 1
        
        if table_start is None:
            return i  # No table found
        
        # Extract header row
        header_row = lines[table_start]
        
        # Find separator row (---) and extract data rows
        i = table_start + 1
        if i < len(lines) and '---' in lines[i]:
            i += 1  # Skip separator
        
        # Collect data rows
        data_rows = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            data_rows.append(lines[i])
            i += 1
        
        # Count TT (first column numeric values)
        tt_count = self._count_tt(data_rows)
        
        # Split table if necessary
        chunks = self._split_by_tt(table_name, header_row, data_rows, tt_count)
        
        self.tables.extend(chunks)
        
        return i
    
    def _count_tt(self, data_rows: List[str]) -> int:
        """Count number of TT (data rows with content)."""
        count = 0
        for row in data_rows:
            # Skip separator rows
            if '---' in row:
                continue

            # Extract first cell content
            cells = [cell.strip() for cell in row.split('|')[1:-1]]
            if cells and len(cells) > 0:
                first_cell = cells[0].strip()
                # Count any non-empty row that's not a separator
                if first_cell and not first_cell.startswith('---'):
                    count += 1
        return count
    
    def _split_by_tt(self, table_name: str, header: str, rows: List[str], 
                     tt_count: int) -> List[Dict]:
        """
        Split table into chunks based on TT threshold.
        
        Args:
            table_name: Name of table (Bảng XX)
            header: Markdown table header row
            rows: List of data rows
            tt_count: Number of TT rows
            
        Returns:
            List of table chunks
        """
        chunks = []
        
        if tt_count < self.TT_THRESHOLD:
            # No split needed
            table_content = self._format_table(header, rows)
            chunks.append({
                'ten_bang': table_name,
                'phan_so': '1/1',
                'tieu_de_muc': self.current_hierarchy.copy(),
                'so_hang_du_lieu': tt_count,
                'noi_dung_bang': table_content
            })
        else:
            # Split into multiple parts
            num_parts = (tt_count + self.ROWS_PER_PART - 1) // self.ROWS_PER_PART
            
            rows_per_part = len(rows) // num_parts if num_parts > 0 else len(rows)
            
            for part_num in range(num_parts):
                start_idx = part_num * rows_per_part
                if part_num == num_parts - 1:
                    # Last part gets remaining rows
                    end_idx = len(rows)
                else:
                    end_idx = (part_num + 1) * rows_per_part
                
                part_rows = rows[start_idx:end_idx]
                part_tt_count = self._count_tt(part_rows)
                
                table_content = self._format_table(header, part_rows)
                
                chunks.append({
                    'ten_bang': table_name,
                    'phan_so': f'{part_num + 1}/{num_parts}',
                    'tieu_de_muc': self.current_hierarchy.copy(),
                    'so_hang_du_lieu': part_tt_count,
                    'noi_dung_bang': table_content
                })
        
        return chunks
    
    def _format_table(self, header: str, rows: List[str]) -> str:
        """Format table markdown (header + separator + rows)."""
        if not rows:
            return header
        
        # Reconstruct with separator
        table_lines = [header]
        # Find separator from original (or create one)
        table_lines.append('| --- | --- | --- | --- | --- | --- | --- |')
        table_lines.extend(rows)
        
        return '\n'.join(table_lines)

