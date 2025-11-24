"""
FastAPI application for the document chunking pipeline.
"""
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
import re
from pydantic import BaseModel
from src.core.stage1_markdown import MarkdownConverter
from src.core.file_cleaner import FileCleaner
from src.core.document_splitter import DocumentSplitter
from src.core.markdown_to_bullet import MarkdownToBulletConverter
from src.core.html_converter import HtmlConverter
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
file_cleaner = FileCleaner()
document_splitter = DocumentSplitter()
bullet_converter = MarkdownToBulletConverter()
html_converter = HtmlConverter()

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


class BulletRequest(BaseModel):
    """Request model for converting text to bullet format."""
    text: str


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


@app.post("/documents/cleanfile")
async def clean_file(file: UploadFile = File(...)):
    """
    Clean document by removing watermarks, headers, and footers.

    Supports PDF and DOCX formats.

    Args:
        file: Document file (PDF or DOCX)

    Returns:
        Cleaned file ready for download
    """
    # Validate file extension
    allowed_extensions = {".pdf", ".docx"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only PDF and DOCX are allowed. Got: {file_ext}"
        )

    logger.info(f"Cleaning file: {file.filename}")

    # Save uploaded file temporarily
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / file.filename

    try:
        # Save file
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        # Clean file
        success, message, output_path = file_cleaner.clean_file(str(temp_file))

        if not success:
            logger.error(f"File cleaning failed: {message}")
            raise HTTPException(status_code=400, detail=message)

        logger.info(f"File cleaned successfully: {output_path}")

        return {
            "status": "success",
            "message": message,
            "filename": Path(output_path).name,
            "output_path": output_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


@app.post("/documents/markdown")
async def convert_to_markdown(
    file: UploadFile = File(...),
    clean_before_convert: bool = True,
):
    """
    Convert document to markdown format.

    Optionally cleans file first (removes watermarks, headers, footers).

    Args:
        file: Document file (PDF, DOCX, PPTX, CSV)
        clean_before_convert: If True, clean PDF/DOCX before conversion (default: True)

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

        # Clean file if requested (for PDF/DOCX only)
        file_to_convert = temp_file
        if clean_before_convert and file_ext in {".pdf", ".docx"}:
            logger.info(f"Cleaning file before conversion: {file.filename}")
            success, message, cleaned_path = file_cleaner.clean_file(str(temp_file))

            if success and cleaned_path:
                file_to_convert = Path(cleaned_path)
                logger.info(f"Using cleaned file: {cleaned_path}")
            else:
                logger.warning(f"File cleaning skipped, using original: {message}")

        # Convert to markdown from file
        logger.info("Converting file to markdown...")
        markdown_result = markdown_converter.convert(str(file_to_convert))
        markdown_content = markdown_result["markdown"]
        logger.info(f"Extracted markdown ({len(markdown_content)} characters)")

        metadata = {
            "source_file": str(file_to_convert),
            "markdown_source": "extracted",
        }

        # Save to sample/markdown_v1.md for review
        sample_dir = Path("sample")
        sample_dir.mkdir(exist_ok=True)
        markdown_output_path = sample_dir / "markdown_v1.md"

        with open(markdown_output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(f"✓ Saved to: {markdown_output_path} (source: {markdown_source})")

        return {
            "filename": file.filename,
            "markdown_content": markdown_content,
            "metadata": metadata,
            "cleaned": clean_before_convert and file_ext in {".pdf", ".docx"},
            "output_file": str(markdown_output_path),
            "message": f"Markdown saved to {markdown_output_path}"
        }

    except Exception as e:
        logger.error(f"Error converting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


@app.post("/documents/split")
async def split_by_table(request: MarkdownChunkRequest):
    """
    Split markdown document by tables with hierarchy preservation.

    Args:
        request: Markdown content to split

    Returns:
        JSON array of table chunks with metadata
    """
    try:
        logger.info("Processing split request...")

        # Parse and split tables
        chunks = document_splitter.parse_markdown(request.markdown_content)

        logger.info(f"Successfully split document into {len(chunks)} chunks")

        return {
            "status": "success",
            "total_chunks": len(chunks),
            "chunks": chunks
        }

    except Exception as e:
        logger.error(f"Error splitting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/bullet")
async def convert_text_to_bullet(request: BulletRequest):
    """
    Convert text/markdown content to bullet list format.

    Converts markdown tables and headings to bullet format with natural language
    arrow conversion (e.g., "Xe ↔ Bãi" → "Xe xuống bãi hoặc từ bãi lên xe")

    Args:
        request: Text content to convert (accepts markdown or N8N extraction format)

    Returns:
        JSON with converted bullet format
    """
    try:
        logger.info("Processing bullet conversion request")

        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text content cannot be empty")

        # Convert to bullet format
        bullet_content = bullet_converter.convert(request.text)

        logger.info("Successfully converted text to bullet format")

        return {
            "status": "success",
            "bullet_content": bullet_content,
            "content_length": len(bullet_content)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting to bullet format: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/download/{filename}")
async def download_file(filename: str):
    """
    Download cleaned or processed file.

    Args:
        filename: Name of the file to download (from temp/cleaned/ directory)

    Returns:
        File for download
    """
    # Security: only allow files from temp/cleaned directory
    # Use absolute path from current working directory
    base_dir = Path.cwd()
    temp_dir = base_dir / "temp" / "cleaned"
    file_path = temp_dir / filename

    logger.debug(f"Download request: filename={filename}, temp_dir={temp_dir}, file_path={file_path}")

    # Prevent directory traversal attacks
    try:
        file_path = file_path.resolve()
        temp_dir = temp_dir.resolve()
        if not str(file_path).startswith(str(temp_dir)):
            logger.warning(f"Access denied: {file_path} not in {temp_dir}")
            raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(status_code=403, detail="Invalid file path")

    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    logger.info(f"Downloading file: {filename} from {file_path}")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.get("/documents/list-files")
async def list_cleaned_files():
    """
    List all cleaned files available for download.

    Returns:
        List of cleaned files with download URLs
    """
    # Use absolute path from current working directory
    base_dir = Path.cwd()
    temp_dir = base_dir / "temp" / "cleaned"
    temp_dir.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Listing files from: {temp_dir}")

    files = []
    if temp_dir.exists():
        for file_path in sorted(temp_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime,
                    "download_url": f"/documents/download/{file_path.name}"
                })

    logger.info(f"Listed {len(files)} cleaned files from {temp_dir}")

    return {
        "total": len(files),
        "files": files
    }


@app.post("/documents/html")
async def convert_to_html(
    file: UploadFile = File(...),
    clean_before_convert: bool = True
):
    """
    Convert document to HTML format.

    Supports: PDF, DOCX, DOC, CSV, PPTX, TXT

    Args:
        file: Document file to convert
        clean_before_convert: Clean file before conversion (PDF/DOCX only)

    Returns:
        HTML content and file path
    """
    allowed_extensions = {".pdf", ".docx", ".doc", ".csv", ".pptx", ".txt"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}. Got: {file_ext}"
        )

    logger.info(f"Converting to HTML: {file.filename}")

    # Save uploaded file temporarily
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / file.filename

    try:
        # Save file
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        # Clean file if requested
        file_to_convert = temp_file
        if clean_before_convert and file_ext in {".pdf", ".docx"}:
            logger.info(f"Cleaning file before conversion: {file.filename}")
            success, message, cleaned_path = file_cleaner.clean_file(str(temp_file))

            if success and cleaned_path:
                file_to_convert = Path(cleaned_path)
                logger.info(f"Using cleaned file: {cleaned_path}")
            else:
                logger.warning(f"File cleaning skipped, using original: {message}")

        # Special handling for CSV
        if file_ext == ".csv":
            csv_content = file_to_convert.read_text(encoding="utf-8")
            html_content = html_converter.csv_to_html(csv_content)

            # Save HTML
            output_dir = Path("sample")
            output_dir.mkdir(exist_ok=True)
            html_filename = f"{Path(file.filename).stem}.html"
            output_path = output_dir / html_filename

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"✓ Converted CSV to HTML: {output_path}")

            return {
                "status": "success",
                "filename": file.filename,
                "format": "html",
                "output_file": str(output_path),
                "message": f"CSV converted to HTML and saved to {output_path}"
            }

        # For other formats: convert to markdown first, then to HTML
        logger.info("Converting file to markdown...")
        markdown_result = markdown_converter.convert(str(file_to_convert))
        markdown_content = markdown_result["markdown"]

        # Convert markdown to HTML
        metadata = markdown_result.get("metadata", {})
        html_content = html_converter.markdown_to_html(markdown_content, metadata)

        # Save HTML
        output_dir = Path("sample")
        output_dir.mkdir(exist_ok=True)
        html_filename = f"{Path(file.filename).stem}.html"
        output_path = output_dir / html_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"✓ Converted to HTML: {output_path}")

        return {
            "status": "success",
            "filename": file.filename,
            "format": "html",
            "output_file": str(output_path),
            "message": f"Document converted to HTML and saved to {output_path}"
        }

    except Exception as e:
        logger.error(f"Error converting to HTML: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


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
