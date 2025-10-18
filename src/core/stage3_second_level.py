"""
Stage 3: Second-level chunking - decompose primary chunks into sub-chunks.
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger

from src.models import Chunk, DocumentSchema, ExtractedListData
from src.extractors.table_extractor import TableExtractor
from src.extractors.metadata_extractor import MetadataExtractor
from src.extractors.vietnamese_parser import VietnameseTextParser


class SecondLevelChunker:
    """Create second-level (sub) chunks from primary chunks."""

    def __init__(self):
        """Initialize second-level chunker."""
        self.table_extractor = TableExtractor()
        self.metadata_extractor = MetadataExtractor()
        self.parser = VietnameseTextParser()

    def chunk_primary_chunk(
        self,
        primary_chunk: Chunk,
        schema: DocumentSchema
    ) -> List[Chunk]:
        """
        Create second-level chunks from a primary chunk.

        Args:
            primary_chunk: First-level chunk
            schema: Document schema

        Returns:
            List of second-level chunks
        """
        sub_chunks = []

        # Get decomposition rules for this chunk type
        decomp_rules = schema.second_level_decomposition.get(primary_chunk.type, [])

        if not decomp_rules:
            logger.debug(f"No decomposition rules for type: {primary_chunk.type}")
            return []

        # Apply decomposition based on chunk type
        if primary_chunk.type == "table":
            sub_chunks = self._decompose_table(primary_chunk, decomp_rules, schema)
        elif primary_chunk.type in ["section", "article", "clause"]:
            sub_chunks = self._decompose_text_section(primary_chunk, decomp_rules, schema)

        logger.info(f"Created {len(sub_chunks)} sub-chunks from {primary_chunk.chunk_id}")
        return sub_chunks

    def _decompose_table(
        self,
        chunk: Chunk,
        rules: List[Dict[str, Any]],
        schema: DocumentSchema
    ) -> List[Chunk]:
        """Decompose table chunk into sub-chunks."""
        sub_chunks = []

        if not chunk.extracted_data:
            return []

        table_dict = chunk.extracted_data.get("table_dict", [])
        headers = chunk.extracted_data.get("headers", [])
        rows = chunk.extracted_data.get("rows", [])

        # Extract row groups by container type
        for rule in rules:
            if rule.get("type") == "row_group":
                group_by = rule.get("group_by")
                if group_by == "container_size":
                    # Group rows by container columns
                    container_cols = chunk.metadata.get("container_columns", {})
                    for container_type, col_idx in container_cols.items():
                        # Create sub-chunk for this container type
                        sub_chunk = self._create_row_group_chunk(
                            chunk, container_type, col_idx, rows, headers
                        )
                        if sub_chunk:
                            sub_chunks.append(sub_chunk)

            elif rule.get("type") == "rule":
                # Extract rules/conditions from table
                extract_type = rule.get("extract")
                patterns = rule.get("patterns", [])

                for pattern in patterns:
                    # Find rows matching pattern
                    matching_rows = self._find_matching_rows(rows, pattern)
                    if matching_rows:
                        sub_chunk = self._create_rule_chunk(
                            chunk, extract_type, matching_rows, headers
                        )
                        if sub_chunk:
                            sub_chunks.append(sub_chunk)

        return sub_chunks

    def _decompose_text_section(
        self,
        chunk: Chunk,
        rules: List[Dict[str, Any]],
        schema: DocumentSchema
    ) -> List[Chunk]:
        """Decompose text section into sub-chunks."""
        sub_chunks = []

        content = chunk.content

        for rule in rules:
            rule_type = rule.get("type")
            patterns = rule.get("patterns", [])

            if rule_type == "clause":
                # Extract numbered clauses
                clauses = self._extract_clauses(content, patterns)
                for idx, clause in enumerate(clauses):
                    sub_chunk = self._create_clause_chunk(chunk, clause, idx)
                    if sub_chunk:
                        sub_chunks.append(sub_chunk)

            elif rule_type == "definition":
                # Extract definitions
                definitions = self._extract_definitions(content, patterns)
                for idx, defn in enumerate(definitions):
                    sub_chunk = self._create_definition_chunk(chunk, defn, idx)
                    if sub_chunk:
                        sub_chunks.append(sub_chunk)

            elif rule_type == "condition":
                # Extract conditions
                conditions = self.metadata_extractor.extract_conditions(content)
                for idx, cond in enumerate(conditions):
                    sub_chunk = self._create_condition_chunk(chunk, cond, idx)
                    if sub_chunk:
                        sub_chunks.append(sub_chunk)

        return sub_chunks

    def _create_row_group_chunk(
        self,
        parent: Chunk,
        container_type: str,
        col_idx: int,
        rows: List[List[str]],
        headers: List[str]
    ) -> Optional[Chunk]:
        """Create chunk for a group of table rows."""

        # Extract relevant data
        group_data = []
        for row in rows:
            if col_idx < len(row) and row[col_idx].strip():
                group_data.append(row)

        if not group_data:
            return None

        # Create content
        content_lines = [f"Container type: {container_type}\n"]
        for row in group_data:
            row_text = " | ".join([f"{headers[i]}: {row[i]}" for i in range(len(row))])
            content_lines.append(row_text)

        content = "\n".join(content_lines)

        # Fix: f-string cannot contain backslash, so process replacement first
        sanitized_type = container_type.replace(' ', '_').replace("'", '')
        chunk_id = f"{parent.chunk_id}_sub_row_{sanitized_type}"

        return Chunk(
            chunk_id=chunk_id,
            document_id=parent.document_id,
            level=2,
            type="row_group",
            title=f"{parent.title} - {container_type}",
            content=content,
            metadata={
                "parent_chunk_id": parent.chunk_id,
                "container_type": container_type,
            },
            relationships=[{
                "type": "parent",
                "target_chunk_id": parent.chunk_id,
                "description": "Parent table",
                "confidence": 1.0,
            }],
            token_count=self.parser.count_tokens(content),
        )

    def _create_rule_chunk(
        self,
        parent: Chunk,
        rule_type: str,
        rows: List[List[str]],
        headers: List[str]
    ) -> Optional[Chunk]:
        """Create chunk for extracted rules."""

        content_lines = [f"Rule type: {rule_type}\n"]
        for row in rows:
            row_text = " | ".join([f"{headers[i]}: {row[i]}" for i in range(min(len(row), len(headers)))])
            content_lines.append(row_text)

        content = "\n".join(content_lines)

        chunk_id = f"{parent.chunk_id}_sub_{rule_type}_{len(rows)}"

        return Chunk(
            chunk_id=chunk_id,
            document_id=parent.document_id,
            level=2,
            type="rule",
            title=f"{parent.title} - {rule_type}",
            content=content,
            metadata={
                "parent_chunk_id": parent.chunk_id,
                "rule_type": rule_type,
            },
            relationships=[{
                "type": "parent",
                "target_chunk_id": parent.chunk_id,
            }],
            token_count=self.parser.count_tokens(content),
        )

    def _find_matching_rows(self, rows: List[List[str]], pattern: str) -> List[List[str]]:
        """Find table rows matching a pattern."""
        matching = []
        for row in rows:
            row_text = " ".join(row)
            if re.search(pattern, row_text, re.IGNORECASE):
                matching.append(row)
        return matching

    def _extract_clauses(self, text: str, patterns: List[str]) -> List[Dict[str, str]]:
        """Extract numbered clauses from text."""
        clauses = []

        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.MULTILINE))
            for i, match in enumerate(matches):
                start = match.start()
                # Find end (next match or end of text)
                end = matches[i + 1].start() if i < len(matches) - 1 else len(text)

                clause_text = text[start:end].strip()
                clauses.append({
                    "number": match.group(1) if match.groups() else str(i + 1),
                    "text": clause_text,
                    "position": start,
                })

        return clauses

    def _extract_definitions(self, text: str, patterns: List[str]) -> List[Dict[str, str]]:
        """Extract definitions from text."""
        definitions = []

        for pattern in patterns:
            # Look for sentences containing definition markers
            sentences = self.parser.split_sentences(text)

            for sentence in sentences:
                if re.search(pattern, sentence, re.IGNORECASE):
                    # Extract term being defined (usually before the marker)
                    term = self._extract_term_from_definition(sentence, pattern)
                    definitions.append({
                        "term": term,
                        "definition": sentence.strip(),
                    })

        return definitions

    def _extract_term_from_definition(self, sentence: str, pattern: str) -> str:
        """Extract the term being defined."""
        # Split at definition marker
        parts = re.split(pattern, sentence, maxsplit=1, flags=re.IGNORECASE)
        if parts:
            # Term is usually in first part
            term = parts[0].strip().split()[-3:]  # Last few words
            return " ".join(term)
        return "Unknown term"

    def _create_clause_chunk(
        self,
        parent: Chunk,
        clause: Dict[str, str],
        index: int
    ) -> Optional[Chunk]:
        """Create chunk for a clause."""

        chunk_id = f"{parent.chunk_id}_sub_clause_{clause['number']}"

        return Chunk(
            chunk_id=chunk_id,
            document_id=parent.document_id,
            level=2,
            type="clause",
            title=f"Khoản {clause['number']}",
            content=clause["text"],
            metadata={
                "parent_chunk_id": parent.chunk_id,
                "clause_number": clause["number"],
            },
            relationships=[{
                "type": "parent",
                "target_chunk_id": parent.chunk_id,
            }],
            token_count=self.parser.count_tokens(clause["text"]),
        )

    def _create_definition_chunk(
        self,
        parent: Chunk,
        definition: Dict[str, str],
        index: int
    ) -> Optional[Chunk]:
        """Create chunk for a definition."""

        chunk_id = f"{parent.chunk_id}_sub_def_{index}"

        return Chunk(
            chunk_id=chunk_id,
            document_id=parent.document_id,
            level=2,
            type="definition",
            title=f"Definition: {definition['term']}",
            content=definition["definition"],
            metadata={
                "parent_chunk_id": parent.chunk_id,
                "term": definition["term"],
            },
            relationships=[{
                "type": "parent",
                "target_chunk_id": parent.chunk_id,
            }],
            token_count=self.parser.count_tokens(definition["definition"]),
        )

    def _create_condition_chunk(
        self,
        parent: Chunk,
        condition: Dict[str, str],
        index: int
    ) -> Optional[Chunk]:
        """Create chunk for a condition."""

        chunk_id = f"{parent.chunk_id}_sub_cond_{index}"

        return Chunk(
            chunk_id=chunk_id,
            document_id=parent.document_id,
            level=2,
            type="condition",
            title=f"Condition: {condition['type']}",
            content=condition["text"],
            metadata={
                "parent_chunk_id": parent.chunk_id,
                "condition_type": condition["type"],
            },
            relationships=[{
                "type": "parent",
                "target_chunk_id": parent.chunk_id,
            }],
            token_count=self.parser.count_tokens(condition["text"]),
        )
