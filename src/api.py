"""
FastAPI application for the document chunking pipeline.
"""
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from loguru import logger
import re
from pydantic import BaseModel
from src.core.stage1_markdown import MarkdownConverter
from src.schemas.schema_loader import get_schema_loader


# Initialize FastAPI app
app = FastAPI(
    title="Document Markdown Chunking API",
    description="Simple API for converting documents to markdown and chunking tables",
    version="1.0.0",
)

# Initialize components
schema_loader = get_schema_loader(schemas_dir="config/schemas")
markdown_converter = MarkdownConverter()

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


class MarkdownChunkRequest(BaseModel):
    """Request model for chunking markdown content."""
    markdown_content: str


class TieuDeMuc(BaseModel):
    """Tiêu đề mục phân cấp."""
    muc_chinh: Optional[str] = None
    muc_cap_1: Optional[str] = None
    muc_cap_2: Optional[str] = None
    muc_cap_3: Optional[str] = None
    muc_cap_4: Optional[str] = None


class MarkdownChunk(BaseModel):
    """Chunk from markdown content."""
    ten_bang: Optional[str] = None
    tieu_de_muc: TieuDeMuc
    noi_dung_bang: str


@app.post("/documents/markdown")
async def convert_to_markdown(
    file: UploadFile = File(...),
):
    """
    Convert document to markdown format.

    Args:
        file: Document file (PDF, DOCX, PPTX, CSV only)

    Returns:
        Markdown content (watermark removed)
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

        # Convert to markdown directly
        markdown_result = markdown_converter.convert(str(temp_file))

        return {
            "filename": file.filename,
            "markdown_content": markdown_result["markdown"],
            "metadata": markdown_result["metadata"]
        }

    except Exception as e:
        logger.error(f"Error converting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


@app.post("/documents/chunk")
async def chunk_markdown(request: MarkdownChunkRequest):
    """
    Chunk markdown content - ONLY extracts tables.
    - 1 table = 1 chunk (or split if >20 data rows, keeping header)
    - Tracks heading hierarchy in separate fields

    Args:
        request: Contains markdown_content to chunk

    Returns:
        List of table chunks with separate heading level fields
    """
    try:
        markdown = request.markdown_content
        chunks = []
        index = 0

        lines = markdown.split('\n')
        i = 0

        # Track heading hierarchy for context
        heading_stack = []  # Stack to maintain hierarchy

        while i < len(lines):
            line = lines[i]
            line_stripped = line.strip()

            # Track headings (###) - ONLY numbered headings and "Bảng XX"
            if line_stripped.startswith('###'):
                heading_text = line_stripped.replace('###', '').strip()

                # Check if it's a numbered heading (II., 1., 1.1., etc.) OR "Bảng XX"
                is_numbered = re.match(r'^([IVX]+\.|[0-9]+(\.[0-9]+)*\.)\s+', heading_text)
                is_table_name = re.match(r'^Bảng\s+\d+', heading_text, re.IGNORECASE)

                if is_numbered:
                    # Extract level from numbering
                    match = re.match(r'^([IVX]+\.|[0-9]+(\.[0-9]+)*\.)', heading_text)
                    numbering = match.group(1)

                    # Determine level (count dots)
                    if re.match(r'^[IVX]+\.', numbering):
                        level = 0  # Roman numerals = top level
                    else:
                        level = numbering.count('.')

                    # Update stack based on level
                    if level < len(heading_stack):
                        heading_stack = heading_stack[:level]

                    if level == len(heading_stack):
                        heading_stack.append(heading_text)
                    else:
                        heading_stack = heading_stack[:level] + [heading_text]

                elif is_table_name:
                    # "Bảng XX" heading - add to stack
                    heading_stack.append(heading_text)

                # Ignore all other ### headings (like text content)

                i += 1

            # ONLY process tables - create chunks
            elif line_stripped.startswith('|'):
                # Collect entire table - consecutive lines starting with |
                table_lines = []
                j = i
                while j < len(lines) and lines[j].strip().startswith('|'):
                    # Only include lines that end with | (complete rows)
                    line_content = lines[j].strip()
                    if line_content.endswith('|'):
                        table_lines.append(lines[j])
                    j += 1

                # Validate table: must have at least header + separator (2 lines)
                if len(table_lines) < 2:
                    i = j
                    continue

                # Check if second line is separator (contains ---)
                second_line = table_lines[1].strip() if len(table_lines) > 1 else ""
                if "---" not in second_line:
                    # Invalid table structure
                    i = j
                    continue

                # Valid table found
                index += 1

                # Extract header (first 2 rows: header + separator)
                header_lines = table_lines[:2]
                data_lines = table_lines[2:] if len(table_lines) > 2 else []

                # Extract heading levels from stack (only numbered headings, not "Bảng XX")
                numbered_headings = [h for h in heading_stack if not re.match(r'^Bảng\s+\d+', h, re.IGNORECASE)]
                h1 = numbered_headings[0] if len(numbered_headings) > 0 else None
                h2 = numbered_headings[1] if len(numbered_headings) > 1 else None
                h3 = numbered_headings[2] if len(numbered_headings) > 2 else None
                h4 = numbered_headings[3] if len(numbered_headings) > 3 else None

                # Table name - only "Bảng XX" items
                table_name_items = [h for h in heading_stack if re.match(r'^Bảng\s+\d+', h, re.IGNORECASE)]
                table_name = table_name_items[-1] if table_name_items else None

                # If table has <= 20 data rows, keep as 1 chunk
                if len(data_lines) <= 20:
                    chunks.append(MarkdownChunk(
                        ten_bang=table_name,
                        tieu_de_muc=TieuDeMuc(
                            muc_chinh=h1,
                            muc_cap_1=h2,
                            muc_cap_2=h3,
                            muc_cap_3=h4,
                            muc_cap_4=None
                        ),
                        noi_dung_bang='\n'.join(table_lines)
                    ))
                else:
                    # Split table into multiple chunks (20 rows each, keep header)
                    chunk_size = 20
                    for part_num, start in enumerate(range(0, len(data_lines), chunk_size), 1):
                        end = min(start + chunk_size, len(data_lines))
                        part_data = data_lines[start:end]

                        # Reconstruct table with header + data slice
                        part_table = header_lines + part_data

                        chunks.append(MarkdownChunk(
                            ten_bang=f"{table_name} - Part {part_num}" if table_name else f"Table Part {part_num}",
                            tieu_de_muc=TieuDeMuc(
                                muc_chinh=h1,
                                muc_cap_1=h2,
                                muc_cap_2=h3,
                                muc_cap_3=h4,
                                muc_cap_4=None
                            ),
                            noi_dung_bang='\n'.join(part_table)
                        ))

                # Skip processed lines
                i = j

            else:
                # Skip all other content
                i += 1

        return chunks

    except Exception as e:
        logger.error(f"Error chunking markdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
