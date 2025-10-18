"""
Document processor orchestrator - coordinates the entire chunking pipeline.
"""
import time
import uuid
from pathlib import Path
from typing import Dict, Any
from loguru import logger

from src.models import (
    DocumentMetadata,
    ChunkingResult,
    ProcessDocumentRequest,
)
from src.schemas.schema_loader import get_schema_loader
from src.core.stage1_markdown import MarkdownConverter
from src.core.stage2_first_level import FirstLevelChunker
from src.core.stage3_second_level import SecondLevelChunker
from src.core.relationship_mapper import RelationshipMapper
from src.storage.chunk_repository import ChunkRepository


class DocumentProcessor:
    """Orchestrates the multi-stage document chunking pipeline."""

    def __init__(self, storage_path: str = "data/chunks"):
        """
        Initialize document processor.

        Args:
            storage_path: Path to store chunks
        """
        self.schema_loader = get_schema_loader()
        self.markdown_converter = MarkdownConverter()
        self.first_level_chunker = FirstLevelChunker()
        self.second_level_chunker = SecondLevelChunker()
        self.relationship_mapper = RelationshipMapper()
        self.repository = ChunkRepository(storage_path)

    def process_document(
        self,
        file_path: str,
        request: ProcessDocumentRequest
    ) -> ChunkingResult:
        """
        Process a document through the complete chunking pipeline.

        Args:
            file_path: Path to document file
            request: Processing request with metadata

        Returns:
            ChunkingResult with processing status and statistics
        """
        start_time = time.time()
        document_id = self._generate_document_id()
        warnings = []

        logger.info(f"Starting document processing: {document_id}")

        try:
            # Stage 1: Convert to Markdown
            logger.info(f"Stage 1: Converting document to markdown")
            markdown_result = self.markdown_converter.convert(file_path)
            markdown_content = markdown_result["markdown"]
            source_metadata = markdown_result["metadata"]

            # Create document metadata
            doc_metadata = self._create_document_metadata(
                document_id,
                request,
                source_metadata
            )

            # Save document metadata
            self.repository.save_document_metadata(doc_metadata)

            # Get schema for document type
            schema = self.schema_loader.get_schema(request.document_type)
            if not schema:
                raise ValueError(f"Schema not found for document type: {request.document_type}")

            # Stage 2: First-level chunking
            logger.info(f"Stage 2: Creating first-level chunks")
            first_level_chunks = self.first_level_chunker.chunk_document(
                markdown_content,
                schema,
                doc_metadata
            )

            if not first_level_chunks:
                warnings.append("No first-level chunks created")

            # Stage 3: Second-level chunking
            logger.info(f"Stage 3: Creating second-level chunks")
            second_level_chunks = []

            for chunk in first_level_chunks:
                sub_chunks = self.second_level_chunker.chunk_primary_chunk(chunk, schema)
                second_level_chunks.extend(sub_chunks)

            # Combine all chunks
            all_chunks = first_level_chunks + second_level_chunks

            # Stage 4: Map relationships
            logger.info(f"Stage 4: Mapping relationships")
            all_chunks = self.relationship_mapper.map_relationships(all_chunks, schema)

            # Validate relationships
            validation = self.relationship_mapper.validate_relationships(all_chunks)
            if validation["stats"]["broken_links"] > 0:
                warnings.append(
                    f"{validation['stats']['broken_links']} broken relationship links found"
                )

            # Save chunks to repository
            logger.info(f"Saving {len(all_chunks)} chunks to repository")
            self.repository.save_chunks(all_chunks)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Create result
            result = ChunkingResult(
                document_id=document_id,
                status="completed",
                chunks_count=len(all_chunks),
                first_level_chunks_count=len(first_level_chunks),
                second_level_chunks_count=len(second_level_chunks),
                processing_time=processing_time,
                warnings=warnings,
            )

            logger.info(
                f"Document processing completed: {document_id} "
                f"({len(all_chunks)} chunks in {processing_time:.2f}s)"
            )

            return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)
            processing_time = time.time() - start_time

            return ChunkingResult(
                document_id=document_id,
                status="failed",
                error_message=str(e),
                processing_time=processing_time,
            )

    def _generate_document_id(self) -> str:
        """Generate unique document ID."""
        return f"doc_{uuid.uuid4().hex[:8]}"

    def _create_document_metadata(
        self,
        document_id: str,
        request: ProcessDocumentRequest,
        source_metadata: Dict[str, Any]
    ) -> DocumentMetadata:
        """Create DocumentMetadata from request and source metadata."""

        return DocumentMetadata(
            document_id=document_id,
            document_name=request.document_name or source_metadata.get("title", "Untitled"),
            document_type=request.document_type,
            source_file=source_metadata.get("source_file", ""),
            effective_date=request.effective_date,
            tags=request.tags,
            custom_metadata=request.custom_metadata,
        )

    def get_document_metadata(self, document_id: str):
        """Get metadata for a document."""
        return self.repository.get_document_metadata(document_id)

    def get_chunks(self, document_id: str, level: int = None):
        """Get chunks for a document."""
        return self.repository.get_chunks(document_id, level)

    def get_chunk_by_id(self, chunk_id: str):
        """Get a specific chunk."""
        return self.repository.get_chunk_by_id(chunk_id)

    def get_related_chunks(self, chunk_id: str, relationship_type: str = None):
        """Get related chunks."""
        return self.repository.get_related_chunks(chunk_id, relationship_type)

    def search_chunks(self, query):
        """Search chunks."""
        return self.repository.search_chunks(query)

    def list_documents(self):
        """List all documents."""
        return self.repository.list_documents()

    def delete_document(self, document_id: str):
        """Delete a document."""
        return self.repository.delete_document(document_id)
