"""
Chunk repository for storing and retrieving chunks.
"""
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from src.models import Chunk, DocumentMetadata, ChunkSearchQuery


class ChunkRepository:
    """Repository for managing document chunks."""

    def __init__(self, storage_path: str = "data/chunks"):
        """
        Initialize chunk repository.

        Args:
            storage_path: Directory to store chunk data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_document_metadata(self, metadata: DocumentMetadata) -> None:
        """Save document metadata."""
        doc_dir = self.storage_path / metadata.document_id
        doc_dir.mkdir(exist_ok=True)

        metadata_file = doc_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Saved metadata for document: {metadata.document_id}")

    def save_chunks(self, chunks: List[Chunk]) -> None:
        """Save chunks to storage."""
        if not chunks:
            return

        document_id = chunks[0].document_id
        doc_dir = self.storage_path / document_id
        doc_dir.mkdir(exist_ok=True)

        # Save level 1 chunks
        level1_chunks = [c for c in chunks if c.level == 1]
        if level1_chunks:
            level1_file = doc_dir / "chunks_level1.json"
            self._save_chunks_to_file(level1_chunks, level1_file)

        # Save level 2 chunks
        level2_chunks = [c for c in chunks if c.level == 2]
        if level2_chunks:
            level2_file = doc_dir / "chunks_level2.json"
            self._save_chunks_to_file(level2_chunks, level2_file)

        logger.info(f"Saved {len(chunks)} chunks for document: {document_id}")

    def _save_chunks_to_file(self, chunks: List[Chunk], file_path: Path) -> None:
        """Save chunks to a JSON file."""
        chunks_data = [chunk.model_dump() for chunk in chunks]

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2, default=str)

    def get_document_metadata(self, document_id: str) -> Optional[DocumentMetadata]:
        """Retrieve document metadata."""
        metadata_file = self.storage_path / document_id / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return DocumentMetadata(**data)

    def get_chunks(
        self,
        document_id: str,
        level: Optional[int] = None
    ) -> List[Chunk]:
        """
        Retrieve chunks for a document.

        Args:
            document_id: Document identifier
            level: Optional level filter (1 or 2)

        Returns:
            List of chunks
        """
        doc_dir = self.storage_path / document_id

        if not doc_dir.exists():
            return []

        chunks = []

        # Load level 1
        if level is None or level == 1:
            level1_file = doc_dir / "chunks_level1.json"
            if level1_file.exists():
                chunks.extend(self._load_chunks_from_file(level1_file))

        # Load level 2
        if level is None or level == 2:
            level2_file = doc_dir / "chunks_level2.json"
            if level2_file.exists():
                chunks.extend(self._load_chunks_from_file(level2_file))

        return chunks

    def _load_chunks_from_file(self, file_path: Path) -> List[Chunk]:
        """Load chunks from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return [Chunk(**chunk_data) for chunk_data in data]

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """Get a specific chunk by ID."""
        # Extract document_id from chunk_id (format: doc_id_...)
        document_id = chunk_id.split("_")[0] + "_" + chunk_id.split("_")[1]

        chunks = self.get_chunks(document_id)

        for chunk in chunks:
            if chunk.chunk_id == chunk_id:
                return chunk

        return None

    def search_chunks(self, query: ChunkSearchQuery) -> List[Chunk]:
        """
        Search chunks based on query criteria.

        Args:
            query: Search query parameters

        Returns:
            List of matching chunks
        """
        # Get all chunks for document or all documents
        if query.document_id:
            chunks = self.get_chunks(query.document_id, level=query.level)
        else:
            # Load all documents
            chunks = []
            for doc_dir in self.storage_path.iterdir():
                if doc_dir.is_dir():
                    chunks.extend(self.get_chunks(doc_dir.name, level=query.level))

        # Apply filters
        filtered_chunks = []

        for chunk in chunks:
            # Type filter
            if query.chunk_type and chunk.type != query.chunk_type:
                continue

            # Document type filter (requires metadata)
            if query.document_type:
                metadata = self.get_document_metadata(chunk.document_id)
                if not metadata or metadata.document_type != query.document_type:
                    continue

            # Metadata filter
            if query.metadata_filter:
                if not self._matches_metadata_filter(chunk, query.metadata_filter):
                    continue

            # Relationship type filter
            if query.relationship_type:
                if not any(rel.type == query.relationship_type for rel in chunk.relationships):
                    continue

            filtered_chunks.append(chunk)

        # Apply pagination
        start = query.offset
        end = start + query.limit

        return filtered_chunks[start:end]

    def _matches_metadata_filter(
        self,
        chunk: Chunk,
        metadata_filter: Dict[str, Any]
    ) -> bool:
        """Check if chunk matches metadata filter."""
        for key, value in metadata_filter.items():
            if key not in chunk.metadata:
                return False

            chunk_value = chunk.metadata[key]

            # Handle list values
            if isinstance(value, list):
                if not isinstance(chunk_value, list):
                    return False
                if not any(v in chunk_value for v in value):
                    return False
            else:
                if chunk_value != value:
                    return False

        return True

    def get_related_chunks(
        self,
        chunk_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Chunk]:
        """
        Get chunks related to a specific chunk.

        Args:
            chunk_id: Source chunk ID
            relationship_type: Optional relationship type filter

        Returns:
            List of related chunks
        """
        chunk = self.get_chunk_by_id(chunk_id)

        if not chunk:
            return []

        related_chunks = []

        for relationship in chunk.relationships:
            if relationship_type and relationship.type != relationship_type:
                continue

            target_chunk = self.get_chunk_by_id(relationship.target_chunk_id)
            if target_chunk:
                related_chunks.append(target_chunk)

        return related_chunks

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in repository."""
        documents = []

        for doc_dir in self.storage_path.iterdir():
            if doc_dir.is_dir():
                metadata = self.get_document_metadata(doc_dir.name)
                if metadata:
                    # Count chunks
                    chunks = self.get_chunks(doc_dir.name)
                    level1_count = len([c for c in chunks if c.level == 1])
                    level2_count = len([c for c in chunks if c.level == 2])

                    documents.append({
                        "document_id": metadata.document_id,
                        "document_name": metadata.document_name,
                        "document_type": metadata.document_type,
                        "uploaded_at": metadata.uploaded_at,
                        "chunks_count": len(chunks),
                        "level1_chunks_count": level1_count,
                        "level2_chunks_count": level2_count,
                    })

        return documents

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks."""
        doc_dir = self.storage_path / document_id

        if not doc_dir.exists():
            return False

        import shutil
        shutil.rmtree(doc_dir)

        logger.info(f"Deleted document: {document_id}")
        return True
