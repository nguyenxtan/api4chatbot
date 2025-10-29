"""
Stage 2: First-level chunking - split markdown into primary semantic chunks.
"""
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from src.models import Chunk, DocumentSchema, DocumentMetadata
from src.extractors.table_extractor import TableExtractor
from src.extractors.metadata_extractor import MetadataExtractor
from src.extractors.vietnamese_parser import VietnameseTextParser


class FirstLevelChunker:
    """Create first-level (primary) chunks from markdown."""

    def __init__(self):
        """Initialize first-level chunker."""
        self.table_extractor = TableExtractor()
        self.metadata_extractor = MetadataExtractor()
        self.parser = VietnameseTextParser()

    def chunk_document(
        self,
        markdown: str,
        schema: DocumentSchema,
        doc_metadata: DocumentMetadata
    ) -> List[Chunk]:
        """
        Create first-level chunks from markdown.

        Args:
            markdown: Markdown content
            schema: Document schema
            doc_metadata: Document metadata

        Returns:
            List of first-level chunks
        """
        logger.info(f"Starting first-level chunking for {doc_metadata.document_id}")

        # Split by boundaries defined in schema
        chunks = []

        # Extract all tables first (they have priority)
        tables_with_context = self.table_extractor.extract_table_with_context(markdown)
        table_positions = [(t["start_line"], t["end_line"]) for t in tables_with_context]

        # Split markdown into lines for processing
        lines = markdown.split("\n")

        # Process non-table sections
        sections = self._split_by_headings(lines, schema, table_positions)

        # Create chunks from sections
        for idx, section in enumerate(sections):
            chunk = self._create_chunk_from_section(
                section,
                idx,
                doc_metadata,
                schema
            )
            if chunk:
                chunks.append(chunk)

        # Create chunks from tables
        for idx, table_info in enumerate(tables_with_context):
            chunk = self._create_chunk_from_table(
                table_info,
                idx,
                doc_metadata,
                schema
            )
            if chunk:
                chunks.append(chunk)

        # Validate chunk sizes
        chunks = self._validate_and_adjust_chunks(chunks, schema)

        logger.info(f"Created {len(chunks)} first-level chunks")
        return chunks

    def _split_by_headings(
        self,
        lines: List[str],
        schema: DocumentSchema,
        table_positions: List[Tuple[int, int]]
    ) -> List[Dict[str, Any]]:
        """Split text by headings while avoiding table regions."""
        sections = []
        current_section = {
            "heading": None,
            "heading_level": 0,
            "content_lines": [],
            "start_line": 0,
        }

        for line_num, line in enumerate(lines):
            # Skip if line is in a table region
            if self._is_in_table_region(line_num, table_positions):
                continue

            # Check if line is a heading
            heading_match = self._match_heading(line, schema)

            if heading_match:
                # Save previous section if it has content
                if current_section["content_lines"]:
                    sections.append(current_section.copy())

                # Start new section
                current_section = {
                    "heading": heading_match["text"],
                    "heading_level": heading_match["level"],
                    "heading_type": heading_match["type"],
                    "content_lines": [],
                    "start_line": line_num,
                }
            else:
                # Add to current section
                current_section["content_lines"].append(line)

        # Add last section
        if current_section["content_lines"]:
            sections.append(current_section)

        return sections

    def _is_in_table_region(
        self,
        line_num: int,
        table_positions: List[Tuple[int, int]]
    ) -> bool:
        """Check if line is within a table region."""
        for start, end in table_positions:
            if start <= line_num <= end:
                return True
        return False

    def _match_heading(
        self,
        line: str,
        schema: DocumentSchema
    ) -> Optional[Dict[str, Any]]:
        """Check if line matches a heading pattern from schema."""

        for boundary in schema.first_level_boundaries:
            if boundary["type"] in ["section", "heading", "chapter", "article", "named_section"]:
                marker = boundary.get("marker")
                markers = boundary.get("markers", [marker] if marker else [])

                for pattern in markers:
                    match = re.match(pattern, line.strip())
                    if match:
                        # Extract heading text
                        heading_text = line.strip()

                        # Determine heading level
                        level = 1
                        if line.startswith("#"):
                            level = len(line) - len(line.lstrip("#"))
                        elif re.match(r"^I+\.", line):
                            level = 1  # Roman numerals = top level
                        elif re.match(r"^\d+\.", line):
                            level = 2  # Arabic numerals = second level

                        return {
                            "text": heading_text,
                            "level": level,
                            "type": boundary["type"],
                        }

        return None

    def _create_chunk_from_section(
        self,
        section: Dict[str, Any],
        index: int,
        doc_metadata: DocumentMetadata,
        schema: DocumentSchema
    ) -> Optional[Chunk]:
        """Create chunk from a text section."""

        content = "\n".join(section["content_lines"]).strip()

        if not content:
            return None

        # Generate chunk ID
        chunk_id = f"{doc_metadata.document_id}_section_{index}"

        # Extract metadata
        metadata = self.metadata_extractor.extract_metadata(
            content,
            schema,
            context=section.get("heading", "")
        )

        # Add section-specific metadata
        if section.get("heading"):
            metadata["heading"] = section["heading"]
            metadata["heading_level"] = section.get("heading_level", 0)

        # Count tokens
        token_count = self.parser.count_tokens(content)

        # Determine chunk type
        chunk_type = "section"
        if "Điều" in section.get("heading", ""):
            chunk_type = "article"
        elif "Chương" in section.get("heading", ""):
            chunk_type = "chapter"

        chunk = Chunk(
            chunk_id=chunk_id,
            document_id=doc_metadata.document_id,
            level=1,
            type=chunk_type,
            title=section.get("heading", f"Section {index}"),
            content=content,
            metadata=metadata,
            relationships=[],
            token_count=token_count,
        )

        return chunk

    def _create_chunk_from_table(
        self,
        table_info: Dict[str, Any],
        index: int,
        doc_metadata: DocumentMetadata,
        schema: DocumentSchema
    ) -> Optional[Chunk]:
        """Create chunk from a table."""

        table = table_info["table"]
        context_before = table_info.get("context_before", "")

        # Generate chunk ID
        table_id = self.table_extractor.extract_table_id(context_before)
        chunk_id_suffix = table_id.replace(" ", "_").lower() if table_id else f"table_{index}"
        chunk_id = f"{doc_metadata.document_id}_{chunk_id_suffix}"

        # Create content: context + table in markdown
        content_parts = []

        if table.caption:
            content_parts.append(f"**{table.caption}**\n")

        # Reconstruct markdown table
        table_md = self._table_to_markdown(table)
        content_parts.append(table_md)

        # Add relevant context
        if context_before:
            # Get last few lines of context
            context_lines = context_before.strip().split("\n")[-3:]
            content_parts.insert(0, "\n".join(context_lines) + "\n")

        content = "\n".join(content_parts)

        # Extract metadata
        metadata = self.metadata_extractor.extract_metadata(
            content,
            schema,
            context=context_before
        )

        # Add table-specific metadata
        metadata["table_id"] = table_id or f"table_{index}"
        metadata["row_count"] = table.row_count
        metadata["column_count"] = table.column_count
        metadata["table_type"] = self.table_extractor.identify_table_type(table)

        # Container type columns
        container_cols = self.table_extractor.extract_container_type_columns(table)
        if container_cols:
            metadata["container_columns"] = container_cols

        # Count tokens
        token_count = self.parser.count_tokens(content)

        # Store structured table data
        extracted_data = {
            "type": "table",
            "headers": table.headers,
            "rows": table.rows,
            "table_dict": self.table_extractor.convert_table_to_dict(table),
        }

        chunk = Chunk(
            chunk_id=chunk_id,
            document_id=doc_metadata.document_id,
            level=1,
            type="table",
            title=table.caption or table_id or f"Table {index}",
            content=content,
            metadata=metadata,
            relationships=[],
            extracted_data=extracted_data,
            token_count=token_count,
        )

        return chunk

    def _table_to_markdown(self, table) -> str:
        """Convert ExtractedTableData to markdown string."""
        lines = []

        # Header row
        header_row = "| " + " | ".join(table.headers) + " |"
        lines.append(header_row)

        # Separator
        separator = "| " + " | ".join(["---"] * table.column_count) + " |"
        lines.append(separator)

        # Data rows
        for row in table.rows:
            row_text = "| " + " | ".join(row) + " |"
            lines.append(row_text)

        return "\n".join(lines)

    def _validate_and_adjust_chunks(
        self,
        chunks: List[Chunk],
        schema: DocumentSchema
    ) -> List[Chunk]:
        """Validate chunk sizes and merge/split if needed."""

        adjusted_chunks = []
        min_tokens = schema.first_level_min_tokens
        max_tokens = schema.first_level_max_tokens

        i = 0
        while i < len(chunks):
            chunk = chunks[i]

            # Check if chunk is too small
            if chunk.token_count < min_tokens and i < len(chunks) - 1:
                # Try to merge with next chunk
                next_chunk = chunks[i + 1]

                # Only merge if combined size is reasonable and same type
                if (chunk.token_count + next_chunk.token_count <= max_tokens and
                    chunk.type == next_chunk.type):

                    merged = self._merge_chunks(chunk, next_chunk)
                    adjusted_chunks.append(merged)
                    i += 2  # Skip next chunk
                    continue

            # Check if chunk is too large
            if chunk.token_count > max_tokens:
                # Split chunk
                split_chunks = self._split_chunk(chunk, max_tokens)
                adjusted_chunks.extend(split_chunks)
            else:
                adjusted_chunks.append(chunk)

            i += 1

        return adjusted_chunks

    def _merge_chunks(self, chunk1: Chunk, chunk2: Chunk) -> Chunk:
        """Merge two chunks together."""

        merged_content = chunk1.content + "\n\n" + chunk2.content
        merged_title = f"{chunk1.title} & {chunk2.title}"

        # Merge metadata
        merged_metadata = chunk1.metadata.copy()
        merged_metadata.update(chunk2.metadata)

        # Recalculate token count
        token_count = self.parser.count_tokens(merged_content)

        return Chunk(
            chunk_id=chunk1.chunk_id + "_merged",
            document_id=chunk1.document_id,
            level=1,
            type=chunk1.type,
            title=merged_title,
            content=merged_content,
            metadata=merged_metadata,
            relationships=[],
            token_count=token_count,
        )

    def _split_chunk(self, chunk: Chunk, max_tokens: int) -> List[Chunk]:
        """Split a large chunk into smaller chunks."""

        # Simple split by paragraphs
        paragraphs = chunk.content.split("\n\n")

        sub_chunks = []
        current_content = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.parser.count_tokens(para)

            if current_tokens + para_tokens > max_tokens and current_content:
                # Create sub-chunk
                sub_chunk = Chunk(
                    chunk_id=f"{chunk.chunk_id}_part{len(sub_chunks) + 1}",
                    document_id=chunk.document_id,
                    level=1,
                    type=chunk.type,
                    title=f"{chunk.title} (Part {len(sub_chunks) + 1})",
                    content="\n\n".join(current_content),
                    metadata=chunk.metadata.copy(),
                    relationships=[],
                    token_count=current_tokens,
                )
                sub_chunks.append(sub_chunk)

                # Reset
                current_content = [para]
                current_tokens = para_tokens
            else:
                current_content.append(para)
                current_tokens += para_tokens

        # Add remaining content
        if current_content:
            sub_chunk = Chunk(
                chunk_id=f"{chunk.chunk_id}_part{len(sub_chunks) + 1}",
                document_id=chunk.document_id,
                level=1,
                type=chunk.type,
                title=f"{chunk.title} (Part {len(sub_chunks) + 1})" if sub_chunks else chunk.title,
                content="\n\n".join(current_content),
                metadata=chunk.metadata.copy(),
                relationships=[],
                token_count=current_tokens,
            )
            sub_chunks.append(sub_chunk)

        return sub_chunks if sub_chunks else [chunk]
