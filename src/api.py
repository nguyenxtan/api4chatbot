"""
FastAPI application for the document chunking pipeline.
"""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from loguru import logger

from src.models import (
    ProcessDocumentRequest,
    ChunkingResult,
    Chunk,
    ChunkSearchQuery,
    DocumentMetadata,
)
from src.core.document_processor import DocumentProcessor
from src.schemas.schema_loader import get_schema_loader


# Initialize FastAPI app
app = FastAPI(
    title="Multi-Document Chunking Pipeline API",
    description="Intelligent document processing with multi-stage chunking for Vietnamese documents",
    version="1.0.0",
)

# Initialize processor
processor = DocumentProcessor(storage_path="data/chunks")
schema_loader = get_schema_loader(schemas_dir="config/schemas")

# Configure logging
logger.add("logs/api.log", rotation="500 MB", retention="10 days", level="INFO")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Document Chunking Pipeline API",
        "version": "1.0.0",
        "status": "running",
        "available_document_types": schema_loader.list_available_schemas(),
    }


@app.post("/documents/markdown")
async def convert_to_markdown(
    file: UploadFile = File(...),
):
    """
    Convert document to markdown format.

    Args:
        file: Document file (PDF, DOCX, PPTX, CSV only)

    Returns:
        Markdown content
    """
    # Validate file extension
    allowed_extensions = {".pdf", ".docx", ".pptx", ".csv"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only PDF, DOCX, PPTX, CSV are allowed. Got: {file_ext}"
        )

    logger.info(f"Converting to markdown: {file.filename}")

    # Save uploaded file temporarily
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / file.filename

    try:
        # Save file
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        # Parse request with default document_type
        request = ProcessDocumentRequest(
            document_type="document",  # Use simple document schema for markdown conversion
            document_name=file.filename,
            effective_date=None,
            tags=[],
        )

        # Process document
        result = processor.process_document(str(temp_file), request)

        return result

    except Exception as e:
        logger.error(f"Error converting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


@app.post("/documents/process", response_model=ChunkingResult)
async def process_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    document_name: Optional[str] = Form(None),
    effective_date: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
):
    """
    Process a document through the chunking pipeline.

    Args:
        file: Document file (PDF, DOCX, MD, TXT)
        document_type: Type of document (pricing, regulation, contract, sop, report)
        document_name: Optional document name
        effective_date: Optional effective date (YYYY-MM-DD)
        tags: Optional comma-separated tags

    Returns:
        ChunkingResult with processing status
    """
    logger.info(f"Processing document: {file.filename} (type: {document_type})")

    # Validate document type
    if document_type not in schema_loader.list_available_schemas():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type. Available types: {schema_loader.list_available_schemas()}"
        )

    # Save uploaded file temporarily
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / file.filename

    try:
        # Save file
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        # Parse request
        request = ProcessDocumentRequest(
            document_type=document_type,
            document_name=document_name or file.filename,
            effective_date=effective_date,
            tags=tags.split(",") if tags else [],
        )

        # Process document
        result = processor.process_document(str(temp_file), request)

        return result

    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


@app.get("/documents", response_model=List[dict])
async def list_documents():
    """List all processed documents."""
    return processor.list_documents()


@app.get("/documents/{document_id}/metadata", response_model=DocumentMetadata)
async def get_document_metadata(document_id: str):
    """Get metadata for a specific document."""
    metadata = processor.get_document_metadata(document_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    return metadata


@app.get("/documents/{document_id}/chunks", response_model=List[Chunk])
async def get_document_chunks(
    document_id: str,
    level: Optional[int] = Query(None, ge=1, le=2, description="Filter by chunk level (1 or 2)"),
    chunk_type: Optional[str] = Query(None, description="Filter by chunk type"),
):
    """
    Get all chunks for a document.

    Args:
        document_id: Document identifier
        level: Optional level filter (1 or 2)
        chunk_type: Optional type filter

    Returns:
        List of chunks
    """
    chunks = processor.get_chunks(document_id, level=level)

    if not chunks:
        raise HTTPException(status_code=404, detail=f"No chunks found for document: {document_id}")

    # Apply type filter if provided
    if chunk_type:
        chunks = [c for c in chunks if c.type == chunk_type]

    return chunks


@app.get("/chunks/{chunk_id}", response_model=Chunk)
async def get_chunk(chunk_id: str):
    """Get a specific chunk by ID."""
    chunk = processor.get_chunk_by_id(chunk_id)

    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk not found: {chunk_id}")

    return chunk


@app.get("/chunks/{chunk_id}/relationships", response_model=List[Chunk])
async def get_chunk_relationships(
    chunk_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
):
    """
    Get chunks related to a specific chunk.

    Args:
        chunk_id: Source chunk ID
        relationship_type: Optional relationship type filter

    Returns:
        List of related chunks
    """
    # Verify source chunk exists
    chunk = processor.get_chunk_by_id(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk not found: {chunk_id}")

    # Get related chunks
    related = processor.get_related_chunks(chunk_id, relationship_type)

    return related


@app.post("/chunks/search", response_model=List[Chunk])
async def search_chunks(query: ChunkSearchQuery):
    """
    Search chunks based on criteria.

    Args:
        query: Search query with filters

    Returns:
        List of matching chunks
    """
    results = processor.search_chunks(query)
    return results


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks."""
    success = processor.delete_document(document_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    return {"status": "success", "message": f"Document {document_id} deleted"}


@app.get("/schemas")
async def list_schemas():
    """List all available document schemas."""
    schemas = schema_loader.get_all_schemas()

    return {
        "count": len(schemas),
        "schemas": [
            {
                "document_type": schema.document_type,
                "description": schema.description,
                "first_level_boundaries": len(schema.first_level_boundaries),
                "metadata_fields": len(schema.first_level_metadata_fields),
                "relationship_patterns": len(schema.relationship_patterns),
            }
            for schema in schemas.values()
        ]
    }


@app.get("/schemas/{document_type}")
async def get_schema(document_type: str):
    """Get full schema for a document type."""
    schema = schema_loader.get_schema(document_type)

    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema not found: {document_type}")

    return schema.model_dump()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "schemas_loaded": len(schema_loader.list_available_schemas()),
    }


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle all uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
