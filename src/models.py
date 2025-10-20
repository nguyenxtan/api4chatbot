"""
Pydantic models for the multi-document chunking pipeline.
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class DocumentMetadata(BaseModel):
    """Metadata for a processed document."""
    document_id: str = Field(..., description="Unique document identifier")
    document_name: str = Field(..., description="Original document name")
    document_type: Literal["pricing", "regulation", "contract", "sop", "report", "document"] = Field(
        ..., description="Document type/category"
    )
    source_file: str = Field(..., description="Source file path")
    uploaded_at: datetime = Field(default_factory=datetime.now, description="Upload timestamp")
    effective_date: Optional[date] = Field(None, description="Document effective date")
    language: str = Field(default="vi", description="Document language")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata fields")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "document_id": "doc_001",
            "document_name": "Biểu giá dịch vụ 2025",
            "document_type": "pricing",
            "source_file": "bieu_gia_2025.pdf",
            "effective_date": "2025-03-10",
            "language": "vi",
            "tags": ["pricing", "container", "2025"]
        }
    })


class Relationship(BaseModel):
    """Represents a relationship between chunks."""
    type: Literal[
        "parent", "child", "reference", "surcharge", "exception",
        "related", "prerequisite", "alternative"
    ] = Field(..., description="Relationship type")
    target_chunk_id: str = Field(..., description="Target chunk ID")
    description: Optional[str] = Field(None, description="Human-readable relationship description")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship confidence score")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "surcharge",
            "target_chunk_id": "doc_001_section_2_3",
            "description": "Phụ thu ngoài giờ",
            "confidence": 0.95
        }
    })


class ExtractedTableData(BaseModel):
    """Structured data extracted from a table."""
    headers: List[str] = Field(..., description="Table column headers")
    rows: List[List[str]] = Field(..., description="Table rows")
    row_count: int = Field(..., description="Number of rows")
    column_count: int = Field(..., description="Number of columns")
    table_id: Optional[str] = Field(None, description="Table identifier (e.g., 'Bảng 01')")
    caption: Optional[str] = Field(None, description="Table caption/title")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "table_id": "Bảng 01",
            "caption": "Cước xếp dỡ container hàng thông thường",
            "headers": ["Phương án làm hàng", "20'", "40'", "45'"],
            "rows": [
                ["Phương án 1", "500,000", "800,000", "900,000"],
                ["Phương án 2", "450,000", "750,000", "850,000"]
            ],
            "row_count": 2,
            "column_count": 4
        }
    })


class ExtractedListData(BaseModel):
    """Structured data extracted from a list."""
    items: List[Dict[str, Any]] = Field(..., description="List items with structure")
    list_type: Literal["ordered", "unordered", "nested"] = Field(..., description="Type of list")
    depth: int = Field(default=1, ge=1, description="Nesting depth")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "list_type": "ordered",
            "depth": 2,
            "items": [
                {"index": "1", "content": "Điều kiện thứ nhất", "subitems": []},
                {"index": "2", "content": "Điều kiện thứ hai", "subitems": [
                    {"index": "a", "content": "Trường hợp a"},
                    {"index": "b", "content": "Trường hợp b"}
                ]}
            ]
        }
    })


class Chunk(BaseModel):
    """Represents a document chunk (level 1 or 2)."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document ID")
    level: Literal[1, 2] = Field(..., description="Chunk level (1=primary, 2=sub-chunk)")
    type: Literal[
        "section", "table", "rule", "clause", "procedure",
        "step", "definition", "condition", "row_group", "metadata",
        "article", "chapter", "heading", "paragraph", "list", "point"
    ] = Field(..., description="Chunk type")
    title: str = Field(..., description="Chunk title/heading")
    content: str = Field(..., description="Chunk text content")

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata (heading_path, page_range, etc.)"
    )

    # Relationships
    relationships: List[Relationship] = Field(
        default_factory=list,
        description="Relationships to other chunks"
    )

    # Structured data (optional)
    extracted_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Extracted structured data (tables, lists, etc.)"
    )

    # Token count for sizing
    token_count: int = Field(default=0, ge=0, description="Approximate token count")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "chunk_id": "doc_001_section_2_1",
            "document_id": "doc_001",
            "level": 1,
            "type": "section",
            "title": "Cước xếp dỡ container",
            "content": "Cước xếp dỡ container được áp dụng theo bảng giá sau...",
            "metadata": {
                "heading_path": "II.Cước Tác Nghiệp > 1.Cước xếp dỡ container",
                "page_range": "4-6",
                "container_types": ["20'", "40'", "45'"]
            },
            "relationships": [
                {
                    "type": "reference",
                    "target_chunk_id": "doc_001_table_23",
                    "description": "Xem Bảng 23"
                }
            ],
            "token_count": 1850
        }
    })


class ChunkingResult(BaseModel):
    """Result of document chunking operation."""
    document_id: str
    status: Literal["processing", "completed", "failed"]
    chunks_count: int = Field(default=0, description="Total number of chunks")
    first_level_chunks_count: int = Field(default=0, description="Number of level 1 chunks")
    second_level_chunks_count: int = Field(default=0, description="Number of level 2 chunks")
    processing_time: float = Field(default=0.0, description="Processing time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "document_id": "doc_001",
            "status": "completed",
            "chunks_count": 45,
            "first_level_chunks_count": 12,
            "second_level_chunks_count": 33,
            "processing_time": 18.5,
            "warnings": ["Table 5 has irregular structure"]
        }
    })


class DocumentSchema(BaseModel):
    """Configuration schema for a document type."""
    document_type: str = Field(..., description="Document type identifier")
    description: str = Field(default="", description="Schema description")

    # First-level chunking configuration
    first_level_boundaries: List[Dict[str, Any]] = Field(
        ...,
        description="Boundary markers for level 1 chunks"
    )
    first_level_metadata_fields: List[str] = Field(
        default_factory=list,
        description="Metadata fields to extract for level 1"
    )

    # Second-level chunking configuration
    second_level_decomposition: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Decomposition rules for level 2 chunks"
    )

    # Relationship patterns
    relationship_patterns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Patterns to identify relationships"
    )

    # Metadata extractors
    metadata_extractors: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata extraction rules"
    )

    # Chunk size limits
    first_level_min_tokens: int = Field(default=1500, description="Minimum tokens for level 1")
    first_level_max_tokens: int = Field(default=3000, description="Maximum tokens for level 1")
    second_level_min_tokens: int = Field(default=500, description="Minimum tokens for level 2")
    second_level_max_tokens: int = Field(default=1500, description="Maximum tokens for level 2")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "document_type": "pricing",
            "description": "Schema for pricing documents",
            "first_level_boundaries": [
                {"type": "section", "marker": "^#+\\s"},
                {"type": "table", "marker": "^\\|.*\\|$"}
            ],
            "first_level_metadata_fields": [
                "heading_path", "page_range", "effective_date", "container_types"
            ],
            "relationship_patterns": [
                {"name": "table_reference", "pattern": "Bảng\\s+(\\d+)", "type": "reference"}
            ]
        }
    })


class ProcessDocumentRequest(BaseModel):
    """Request model for document processing."""
    document_type: Literal["pricing", "regulation", "contract", "sop", "report", "document"]
    document_name: Optional[str] = None
    effective_date: Optional[date] = None
    tags: List[str] = Field(default_factory=list)
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkSearchQuery(BaseModel):
    """Query model for searching chunks."""
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    level: Optional[Literal[1, 2]] = None
    chunk_type: Optional[str] = None
    metadata_filter: Dict[str, Any] = Field(default_factory=dict)
    relationship_type: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
