"""
Relationship mapper - identifies and maps relationships between chunks.
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger

from src.models import Chunk, Relationship, DocumentSchema
from src.extractors.vietnamese_parser import VietnameseTextParser


class RelationshipMapper:
    """Map relationships between chunks."""

    def __init__(self):
        """Initialize relationship mapper."""
        self.parser = VietnameseTextParser()

    def map_relationships(
        self,
        chunks: List[Chunk],
        schema: DocumentSchema
    ) -> List[Chunk]:
        """
        Identify and map relationships between chunks.

        Args:
            chunks: List of all chunks (level 1 and 2)
            schema: Document schema with relationship patterns

        Returns:
            Updated chunks with relationships
        """
        logger.info(f"Mapping relationships for {len(chunks)} chunks")

        # Create lookup dict for chunks by ID
        chunk_dict = {chunk.chunk_id: chunk for chunk in chunks}

        # Process each chunk
        for chunk in chunks:
            # Map cross-references
            self._map_cross_references(chunk, chunks, chunk_dict, schema)

            # Map hierarchical relationships (parent-child)
            self._map_hierarchical_relationships(chunk, chunks, chunk_dict)

            # Map domain-specific relationships (surcharge, exception, etc.)
            self._map_domain_relationships(chunk, chunks, chunk_dict, schema)

        logger.info("Relationship mapping complete")
        return chunks

    def _map_cross_references(
        self,
        chunk: Chunk,
        all_chunks: List[Chunk],
        chunk_dict: Dict[str, Chunk],
        schema: DocumentSchema
    ) -> None:
        """Map cross-references between chunks."""

        content = chunk.content

        for pattern_config in schema.relationship_patterns:
            pattern = pattern_config.get("pattern")
            rel_type = pattern_config.get("type", "reference")
            description = pattern_config.get("description", "")

            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                reference_text = match.group(0)

                # Try to resolve reference to actual chunk
                target_chunk = self._resolve_reference(reference_text, all_chunks, pattern_config)

                if target_chunk:
                    # Add relationship
                    relationship = Relationship(
                        type=rel_type,
                        target_chunk_id=target_chunk.chunk_id,
                        description=f"{description}: {reference_text}",
                        confidence=0.9,
                    )

                    # Avoid duplicates
                    if not self._has_relationship(chunk, relationship):
                        chunk.relationships.append(relationship)

    def _resolve_reference(
        self,
        reference_text: str,
        all_chunks: List[Chunk],
        pattern_config: Dict[str, Any]
    ) -> Optional[Chunk]:
        """Resolve a reference text to an actual chunk."""

        # Extract reference identifier
        ref_id = self._extract_reference_id(reference_text, pattern_config)

        if not ref_id:
            return None

        # Search for chunk with matching identifier
        for chunk in all_chunks:
            # Check metadata
            if self._chunk_matches_reference(chunk, ref_id, reference_text):
                return chunk

        return None

    def _extract_reference_id(self, text: str, pattern_config: Dict) -> Optional[str]:
        """Extract identifier from reference text."""
        # Table references: "Bảng 23" -> "23"
        if "Bảng" in text:
            match = re.search(r"Bảng\s+([\d\w-]+)", text, re.IGNORECASE)
            return match.group(1) if match else None

        # Article references: "Điều 15" -> "15"
        if "Điều" in text:
            match = re.search(r"Điều\s+(\d+)", text)
            return match.group(1) if match else None

        # Clause references: "Khoản 3" -> "3"
        if "Khoản" in text:
            match = re.search(r"Khoản\s+(\d+)", text)
            return match.group(1) if match else None

        return None

    def _chunk_matches_reference(self, chunk: Chunk, ref_id: str, ref_text: str) -> bool:
        """Check if chunk matches a reference."""

        # Check table_id
        if chunk.type == "table":
            table_id = chunk.metadata.get("table_id", "")
            if ref_id in table_id:
                return True

        # Check article number
        if chunk.type == "article":
            article_num = chunk.metadata.get("article_number", "")
            if ref_id == article_num:
                return True

        # Check clause number
        if chunk.type == "clause":
            clause_num = chunk.metadata.get("clause_number", "")
            if ref_id == clause_num:
                return True

        # Check title/heading
        if ref_text.lower() in chunk.title.lower():
            return True

        return False

    def _map_hierarchical_relationships(
        self,
        chunk: Chunk,
        all_chunks: List[Chunk],
        chunk_dict: Dict[str, Chunk]
    ) -> None:
        """Map parent-child relationships."""

        # If chunk has parent_chunk_id in metadata, create parent relationship
        parent_id = chunk.metadata.get("parent_chunk_id")
        if parent_id and parent_id in chunk_dict:
            relationship = Relationship(
                type="parent",
                target_chunk_id=parent_id,
                description="Parent chunk",
                confidence=1.0,
            )
            if not self._has_relationship(chunk, relationship):
                chunk.relationships.append(relationship)

        # Find child chunks
        for other_chunk in all_chunks:
            if other_chunk.metadata.get("parent_chunk_id") == chunk.chunk_id:
                relationship = Relationship(
                    type="child",
                    target_chunk_id=other_chunk.chunk_id,
                    description="Child chunk",
                    confidence=1.0,
                )
                if not self._has_relationship(chunk, relationship):
                    chunk.relationships.append(relationship)

    def _map_domain_relationships(
        self,
        chunk: Chunk,
        all_chunks: List[Chunk],
        chunk_dict: Dict[str, Chunk],
        schema: DocumentSchema
    ) -> None:
        """Map domain-specific relationships (surcharge, exception, etc.)."""

        content = chunk.content.lower()

        # Surcharge relationships
        if "phụ thu" in content:
            # This chunk mentions surcharges
            # Find actual surcharge chunks
            for other_chunk in all_chunks:
                if (other_chunk.type == "rule" and
                    other_chunk.metadata.get("rule_type") == "surcharges"):

                    relationship = Relationship(
                        type="surcharge",
                        target_chunk_id=other_chunk.chunk_id,
                        description="Surcharge rule",
                        confidence=0.8,
                    )
                    if not self._has_relationship(chunk, relationship):
                        chunk.relationships.append(relationship)

        # Exception relationships
        if any(marker in content for marker in ["ngoài trừ", "không áp dụng", "trừ trường hợp"]):
            for other_chunk in all_chunks:
                if other_chunk.type == "exception" or other_chunk.metadata.get("condition_type") == "exception":
                    relationship = Relationship(
                        type="exception",
                        target_chunk_id=other_chunk.chunk_id,
                        description="Exception rule",
                        confidence=0.8,
                    )
                    if not self._has_relationship(chunk, relationship):
                        chunk.relationships.append(relationship)

    def _has_relationship(self, chunk: Chunk, relationship: Relationship) -> bool:
        """Check if chunk already has this relationship."""
        for existing in chunk.relationships:
            if (existing.type == relationship.type and
                existing.target_chunk_id == relationship.target_chunk_id):
                return True
        return False

    def validate_relationships(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """
        Validate relationship integrity.

        Returns:
            Validation report with broken links, etc.
        """
        chunk_ids = {chunk.chunk_id for chunk in chunks}
        broken_links = []
        stats = {
            "total_relationships": 0,
            "broken_links": 0,
            "relationship_types": {},
        }

        for chunk in chunks:
            for rel in chunk.relationships:
                stats["total_relationships"] += 1

                # Count by type
                rel_type = rel.type
                stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1

                # Check if target exists
                if rel.target_chunk_id not in chunk_ids:
                    broken_links.append({
                        "source_chunk": chunk.chunk_id,
                        "target_chunk": rel.target_chunk_id,
                        "relationship_type": rel.type,
                    })
                    stats["broken_links"] += 1

        logger.info(f"Relationship validation: {stats['broken_links']} broken links out of {stats['total_relationships']} total")

        return {
            "stats": stats,
            "broken_links": broken_links,
        }
