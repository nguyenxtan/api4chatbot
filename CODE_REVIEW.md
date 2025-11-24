# CODE REVIEW & ANALYSIS REPORT

## Tóm tắt
Báo cáo phân tích chi tiết 3 câu hỏi của bạn về dự án API conversion document.

---

## CÂU HỎI 1: Tại sao khi sử dụng API markdown từ 1 file DOCX khác lại ra dữ liệu như file PDF trong sample?

### NGUYÊN NHÂN: Hardcode Reference Markdown

Trong file [src/api.py:189-199](src/api.py#L189-L199), có một **hardcode lớn**:

```python
# Check if reference markdown.md exists (for PDFs with encoding issues)
reference_markdown_path = Path("sample") / "markdown.md"
markdown_content = None
markdown_source = "extracted"

if reference_markdown_path.exists():
    logger.info(f"Found reference markdown: {reference_markdown_path}")
    with open(reference_markdown_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    markdown_source = "reference"
    logger.info(f"Using reference markdown ({len(markdown_content)} characters)")
else:
    # Convert to markdown from file
    logger.info("Converting file to markdown...")
    markdown_result = markdown_converter.convert(str(file_to_convert))
    markdown_content = markdown_result["markdown"]
    logger.info(f"Extracted markdown ({len(markdown_content)} characters)")
```

### VẤN ĐỀ:
- **Khi file `sample/markdown.md` tồn tại**, API sẽ **luôn dùng file này** thay vì convert từ file bạn upload
- Không cần quan tâm bạn upload file gì (DOCX, PDF, PPTX, CSV), nó sẽ trả về nội dung của `sample/markdown.md`
- Đây là lý do tại sao bạn upload file DOCX khác nhưng vẫn nhận được dữ liệu từ PDF (vì `sample/markdown.md` là từ file PDF)

### KIỂM CHỨNG:
File `sample/markdown.md` hiện tại (743 KB) chứa dữ liệu từ file PDF:
- `508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf` (743 KB)

**Đây là lỗi nghiêm trọng vì:**
1. **Mục đích của function**: `convert_markdown()` nên convert từ file được upload
2. **Tính năng bị bypass**: Việc upload file mới hoàn toàn vô nghĩa
3. **Data leakage**: Mọi file upload đều nhận cùng 1 kết quả
4. **Hard to debug**: Người dùng không biết tại sao file của họ không được xử lý

### GIẢI PHÁP:
**Option 1** (Recommended): Xóa check reference markdown
```python
# REMOVE: Check if reference markdown.md exists
# Luôn convert từ file được upload
markdown_result = markdown_converter.convert(str(file_to_convert))
markdown_content = markdown_result["markdown"]
```

**Option 2**: Thêm parameter để opt-in reference markdown
```python
@app.post("/documents/markdown")
async def convert_markdown(
    file: UploadFile = File(...),
    clean_before_convert: bool = True,
    use_reference: bool = False  # NEW
):
    if use_reference:
        # Use reference markdown if exists
    else:
        # Always convert from uploaded file
```

---

## CÂU HỎI 2: Xây dựng API convert từ DOCX, DOC, CSV... sang HTML

### KIẾN TRÚC GIẢI PHÁP

#### Bước 1: Cấp nhật MarkdownConverter để hỗ trợ xuất HTML

File: [src/core/stage1_markdown.py](src/core/stage1_markdown.py)

```python
def convert(self, file_path: str, output_format: str = "markdown") -> Dict[str, Any]:
    """
    Convert document to specified format (markdown, html, json).

    Args:
        file_path: Path to document file
        output_format: Output format ("markdown", "html", "json", "docx", "pdf")
    """
    # 1. Convert to markdown first (as intermediate format)
    markdown_result = self._convert_to_markdown(file_path)

    # 2. Convert markdown to target format
    if output_format == "html":
        return self._markdown_to_html(markdown_result["markdown"], markdown_result["metadata"])
    elif output_format == "json":
        return self._markdown_to_json(markdown_result["markdown"], markdown_result["metadata"])
    else:
        return markdown_result
```

#### Bước 2: Thêm HTML conversion utility

File: `src/core/html_converter.py` (file mới)

```python
"""
Convert markdown to HTML with support for tables, formatting, etc.
"""
import markdown
from markdownify import markdownify as md
from typing import Dict, Any

class HtmlConverter:
    """Convert markdown to HTML."""

    def markdown_to_html(self, markdown_content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Convert markdown content to HTML.

        Args:
            markdown_content: Markdown text
            metadata: Optional metadata for HTML header

        Returns:
            HTML content
        """
        # Use python-markdown library with extensions
        html = markdown.markdown(
            markdown_content,
            extensions=[
                'tables',           # Support for tables
                'fenced_code',      # Support for code blocks
                'nl2br',            # Convert newlines to <br>
                'toc',              # Table of contents
                'extra',            # Extra features (abbreviations, footnotes)
            ]
        )

        # Wrap in HTML document with metadata
        full_html = self._wrap_in_html_document(html, metadata)
        return full_html

    def _wrap_in_html_document(self, html_body: str, metadata: Dict[str, Any] = None) -> str:
        """Wrap HTML body in proper HTML document structure."""
        title = metadata.get("title", "Document") if metadata else "Document"

        return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
            margin-top: 30px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>"""

    def csv_to_html_table(self, csv_content: str) -> str:
        """
        Convert CSV to HTML table.

        Args:
            csv_content: CSV text

        Returns:
            HTML table
        """
        import csv
        from io import StringIO

        reader = csv.reader(StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return ""

        html = '<table>\n'

        # First row as header
        html += '<thead>\n<tr>\n'
        for cell in rows[0]:
            html += f'<th>{cell.strip()}</th>\n'
        html += '</tr>\n</thead>\n'

        # Remaining rows as body
        html += '<tbody>\n'
        for row in rows[1:]:
            html += '<tr>\n'
            for cell in row:
                html += f'<td>{cell.strip()}</td>\n'
            html += '</tr>\n'
        html += '</tbody>\n'

        html += '</table>'
        return html
```

#### Bước 3: Thêm API endpoint mới

File: [src/api.py](src/api.py)

```python
from src.core.html_converter import HtmlConverter

html_converter = HtmlConverter()

@app.post("/documents/convert")
async def convert_document(
    file: UploadFile = File(...),
    output_format: str = "html",  # html, markdown, json
    clean_before_convert: bool = True
):
    """
    Convert document to specified format (HTML, Markdown, JSON).

    Supports: PDF, DOCX, DOC, CSV, PPTX, TXT

    Args:
        file: Document file to convert
        output_format: Target format (html, markdown, json)
        clean_before_convert: Clean file before conversion

    Returns:
        Converted content in requested format
    """
    allowed_extensions = {".pdf", ".docx", ".doc", ".csv", ".pptx", ".txt"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {allowed_extensions}. Got: {file_ext}"
        )

    if output_format not in {"html", "markdown", "json"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported output format: {output_format}. Allowed: html, markdown, json"
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

        # Clean file if requested
        file_to_convert = temp_file
        if clean_before_convert and file_ext in {".pdf", ".docx"}:
            success, message, cleaned_path = file_cleaner.clean_file(str(temp_file))
            if success and cleaned_path:
                file_to_convert = Path(cleaned_path)

        # Special handling for CSV
        if file_ext == ".csv":
            csv_content = file_to_convert.read_text(encoding="utf-8")

            if output_format == "html":
                html_table = html_converter.csv_to_html_table(csv_content)
                return {
                    "status": "success",
                    "filename": file.filename,
                    "format": "html",
                    "content": html_table,
                    "message": f"CSV converted to HTML table"
                }
            elif output_format == "markdown":
                # Convert CSV to markdown table
                import csv
                from io import StringIO
                reader = csv.reader(StringIO(csv_content))
                rows = list(reader)

                md_table = "| " + " | ".join(rows[0]) + " |\n"
                md_table += "|" + "|".join(["---"] * len(rows[0])) + "|\n"
                for row in rows[1:]:
                    md_table += "| " + " | ".join(row) + " |\n"

                return {
                    "status": "success",
                    "filename": file.filename,
                    "format": "markdown",
                    "content": md_table
                }

        # Convert document to markdown first
        markdown_result = markdown_converter.convert(str(file_to_convert))
        markdown_content = markdown_result["markdown"]

        # Convert to target format
        if output_format == "html":
            html_content = html_converter.markdown_to_html(
                markdown_content,
                markdown_result.get("metadata", {})
            )

            # Save HTML
            output_dir = Path("sample")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{Path(file.filename).stem}.html"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            return {
                "status": "success",
                "filename": file.filename,
                "format": "html",
                "content": html_content,
                "output_file": str(output_path),
                "message": f"Converted to HTML and saved to {output_path}"
            }

        elif output_format == "markdown":
            return {
                "status": "success",
                "filename": file.filename,
                "format": "markdown",
                "content": markdown_content
            }

        elif output_format == "json":
            # Split into chunks and return as JSON
            chunks = document_splitter.parse_markdown(markdown_content)
            return {
                "status": "success",
                "filename": file.filename,
                "format": "json",
                "total_chunks": len(chunks),
                "chunks": chunks
            }

    except Exception as e:
        logger.error(f"Error converting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


@app.post("/documents/html")
async def convert_to_html(file: UploadFile = File(...)):
    """
    Quick endpoint to convert any document to HTML.
    Shorthand for /documents/convert with output_format=html
    """
    return await convert_document(file, output_format="html")


@app.post("/documents/markdown")  # Keep existing endpoint for compatibility
async def convert_markdown(
    file: UploadFile = File(...),
    clean_before_convert: bool = True
):
    """Legacy endpoint for markdown conversion."""
    return await convert_document(file, output_format="markdown", clean_before_convert=clean_before_convert)
```

#### Bước 4: Cập nhật requirements.txt

```
markdown==3.5.1  # For markdown processing
markdownify==0.11.6  # For converting HTML back to markdown if needed
```

### API USAGE EXAMPLES

**Convert DOCX to HTML:**
```bash
curl -X POST "http://localhost:8000/documents/convert" \
  -F "file=@document.docx" \
  -F "output_format=html"
```

**Convert CSV to HTML:**
```bash
curl -X POST "http://localhost:8000/documents/convert" \
  -F "file=@data.csv" \
  -F "output_format=html"
```

**Convert PDF to JSON:**
```bash
curl -X POST "http://localhost:8000/documents/convert" \
  -F "file=@document.pdf" \
  -F "output_format=json"
```

**Quick HTML conversion:**
```bash
curl -X POST "http://localhost:8000/documents/html" \
  -F "file=@document.docx"
```

---

## CÂU HỎI 3: Review toàn bộ code xem có hardcode giống như lỗi số 1 không?

### PHÁT HIỆN HARDCODES

#### ⚠️ **CRITICAL HARDCODES** (Cần fix ngay)

##### 1. **Reference Markdown Path** (src/api.py:190)
```python
reference_markdown_path = Path("sample") / "markdown.md"
```
**Severity**: ⚠️⚠️⚠️ **CRITICAL** - Bypass toàn bộ conversion logic
**Impact**: Mọi file upload đều trả về dữ liệu từ file cụ thể
**Fix**: Xóa logic này hoặc thêm parameter opt-in

##### 2. **Page Start Threshold** (src/core/stage1_markdown.py:133)
```python
if page_num >= 4 and not started_processing:
    started_processing = True
```
**Severity**: ⚠️⚠️ **HIGH** - Cứng cho PDF cụ thể
**Impact**: Chỉ hoạt động cho document có Section II bắt đầu từ trang 4
**Fix**: Move vào schema configuration

##### 3. **PDF Section Detection** (src/core/stage1_markdown.py:179)
```python
if not started_processing and "II." in line_text and "CƯỚC" in line_text:
    started_processing = True
```
**Severity**: ⚠️⚠️ **HIGH** - Cứng cho Vietnamese pricing documents
**Impact**: Không thể xử lý document không có "II. CƯỚC"
**Fix**: Configurable section markers

##### 4. **Font Size Thresholds** (src/core/stage1_markdown.py:195-200)
```python
if avg_font_size > 16:           # Level 1 heading
elif avg_font_size > 14:         # Level 2 heading
elif avg_font_size > 12:         # Level 3 heading
```
**Severity**: ⚠️ **MEDIUM** - Phụ thuộc vào font của document
**Impact**: Heading levels có thể không chính xác với PDF khác
**Fix**: Configurable per document type

##### 5. **File Paths (Multiple locations)**

| File | Line | Path | Severity |
|------|------|------|----------|
| src/api.py | 26 | `"config/schemas"` | ⚠️⚠️ |
| src/api.py | 99, 167, 323 | `"temp"` | ⚠️⚠️ |
| src/api.py | 213, 190 | `"sample"` | ⚠️⚠️ |
| src/core/file_cleaner.py | 27 | `"temp/cleaned"` | ⚠️⚠️ |
| src/schemas/schema_loader.py | 16 | `"config/schemas"` | ⚠️⚠️ |

**Fix**: Use environment variables

#### ⚠️ **MEDIUM HARDCODES** (Nên fix)

##### 6. **Port Numbers** (src/api.py:399, run.py:16, Dockerfile:39)
```python
# src/api.py:399
uvicorn.run(app, host="0.0.0.0", port=8000)

# run.py:16
uvicorn.run(app, host="0.0.0.0", port=8000)

# Dockerfile:39
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8005"]
```
**Severity**: ⚠️ **MEDIUM** - Conflict (8000 vs 8005)
**Impact**: Multiple processes can't run on same port
**Fix**: Use environment variables

##### 7. **PDF Watermark Patterns** (src/core/stage1_markdown.py:92-99)
```python
watermark_patterns = [
    r"(?i)watermark",
    r"(?i)draft",
    r"(?i)confidential",
    r"(?i)do not copy",
    r"(?i)internal use only",
    r"(?i)approved",
    r"_Approved",
]
```
**Severity**: ⚠️ **MEDIUM** - Generic but hardcoded
**Impact**: Can't customize for specific document types
**Fix**: Move to schema

##### 8. **PDF Metadata Keywords** (src/core/markdown_to_bullet.py:463-468)
```python
metadata_lines = [
    'người in:', 'người ký:', 'thủ trưởng', 'email', '.vn',
    'điện thoại', 'ngày in:', 'fax:', 'địa chỉ:', 'tổng công ty'
]
```
**Severity**: ⚠️ **MEDIUM** - Vietnamese-specific
**Impact**: Can't reuse for other languages
**Fix**: Move to schema

##### 9. **Table Border Characters** (src/core/markdown_to_bullet.py)
```python
# Line 447-448: Box drawing characters
'┃', '┣', '━', '─'
```
**Severity**: ⚠️ **LOW** - Reasonable default
**Impact**: Output format is fixed
**Fix**: Optional

##### 10. **Container Size Patterns** (src/core/markdown_to_bullet.py:673)
```python
r"(\d+[''ʼ\u2019](?:\s*&\s*\d+[''ʼ\u2019])?)"
# Matches: 20', 40', 45', 20' & 45'
```
**Severity**: ⚠️⚠️ **HIGH** - Domain-specific
**Impact**: Only works for container/shipping documents
**Fix**: Move to schema

#### ✅ **LOW HARDCODES** (Tập trung)

##### 11. **Pagination Thresholds** (src/core/file_cleaner.py:163-164)
```python
header_threshold = page_height * 0.90  # Top 10% of page
footer_threshold = page_height * 0.10  # Bottom 10% of page
```
**Severity**: ✅ **LOW** - Percentage-based, reasonable
**Impact**: Minor
**Note**: Good design

##### 12. **Page Dimension** (src/core/file_cleaner.py:319)
```python
page_width = 595  # Standard A4 PDF width
```
**Severity**: ✅ **LOW** - A4 is standard
**Impact**: Works for most PDFs
**Note**: Good default

##### 13. **Log Rotation** (src/api.py:33)
```python
logger.add("logs/api.log", rotation="500 MB", retention="10 days", level="INFO")
```
**Severity**: ✅ **LOW** - Reasonable defaults
**Impact**: Minimal
**Note**: Can be made configurable if needed

---

### HARDCODE SUMMARY TABLE

| # | Location | Issue | Severity | Fix Priority |
|----|----------|-------|----------|--------------|
| 1 | src/api.py:190 | Reference markdown bypass | 🔴 CRITICAL | 🔥 URGENT |
| 2 | src/core/stage1_markdown.py:133 | Page >= 4 threshold | 🟠 HIGH | 🔥 URGENT |
| 3 | src/core/stage1_markdown.py:179 | "II. CƯỚC" detection | 🟠 HIGH | 🔥 URGENT |
| 4 | src/core/stage1_markdown.py:195-200 | Font size thresholds | 🟡 MEDIUM | ⚠️ SOON |
| 5 | Multiple files | File paths (temp, sample, config) | 🟠 HIGH | 🔥 URGENT |
| 6 | Port numbers | 8000/8005 conflict | 🟡 MEDIUM | ⚠️ SOON |
| 7 | stage1_markdown.py:92-99 | Watermark patterns | 🟡 MEDIUM | ⚠️ SOON |
| 8 | markdown_to_bullet.py:463-468 | Metadata keywords | 🟡 MEDIUM | ⚠️ SOON |
| 9 | markdown_to_bullet.py | Box drawing chars | 🟢 LOW | ℹ️ NICE |
| 10 | markdown_to_bullet.py:673 | Container size regex | 🟠 HIGH | 🔥 URGENT |
| 11 | file_cleaner.py:163-164 | Header/footer threshold | 🟢 LOW | ℹ️ NICE |
| 12 | file_cleaner.py:319 | Page width (595pt) | 🟢 LOW | ℹ️ NICE |
| 13 | api.py:33 | Log rotation | 🟢 LOW | ℹ️ NICE |

---

### GIẢI PHÁP TỔNG QUÁT: ENVIRONMENT-BASED CONFIG

Tạo file `.env`:
```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# File Paths
TEMP_DIR=temp
SAMPLE_DIR=sample
SCHEMAS_DIR=config/schemas
CLEANED_FILES_DIR=temp/cleaned

# PDF Processing
PDF_PROCESSING_START_PAGE=4
PDF_SECTION_MARKER_1=II.
PDF_SECTION_MARKER_2=CƯỚC
PDF_FONT_SIZE_THRESHOLD_H1=16
PDF_FONT_SIZE_THRESHOLD_H2=14
PDF_FONT_SIZE_THRESHOLD_H3=12

# PDF Header/Footer
PDF_HEADER_THRESHOLD_PERCENT=0.90
PDF_FOOTER_THRESHOLD_PERCENT=0.10

# Document Processing
ENABLE_REFERENCE_MARKDOWN=false  # FIX: Should be false by default

# Logging
LOG_FILE=logs/api.log
LOG_ROTATION_SIZE=500 MB
LOG_RETENTION_DAYS=10
```

Update `src/config.py`:
```python
from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # Paths
    temp_dir: str = os.getenv("TEMP_DIR", "temp")
    sample_dir: str = os.getenv("SAMPLE_DIR", "sample")
    schemas_dir: str = os.getenv("SCHEMAS_DIR", "config/schemas")

    # PDF Processing
    pdf_start_page: int = int(os.getenv("PDF_PROCESSING_START_PAGE", "4"))
    pdf_section_markers: list = [
        os.getenv("PDF_SECTION_MARKER_1", "II."),
        os.getenv("PDF_SECTION_MARKER_2", "CƯỚC")
    ]
    pdf_font_h1: float = float(os.getenv("PDF_FONT_SIZE_THRESHOLD_H1", "16"))
    pdf_font_h2: float = float(os.getenv("PDF_FONT_SIZE_THRESHOLD_H2", "14"))
    pdf_font_h3: float = float(os.getenv("PDF_FONT_SIZE_THRESHOLD_H3", "12"))

    # Features
    enable_reference_markdown: bool = os.getenv("ENABLE_REFERENCE_MARKDOWN", "false").lower() == "true"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## TÓNG TẮT & KHUYẾN NGHỊ

### Tình Hình Hiện Tại
- ✅ Code architecture: Tốt (modular, clean)
- ❌ Configuration: Tệ (quá nhiều hardcode)
- ❌ Flexibility: Kém (chỉ hoạt động cho 1 document type)
- ❌ Maintainability: Khó (hardcode phân tán)

### Ưu Tiên Fix
1. **URGENT**: Fix reference markdown hardcode (CÂU HỎI 1 của bạn)
2. **URGENT**: Move all file paths to environment variables
3. **URGENT**: Move PDF processing thresholds to schema
4. **SOON**: Create .env configuration system
5. **NICE**: Implement HTML conversion (CÂU HỎI 2 của bạn)

### Benefit của Config-based Approach
- ✅ Có thể xử lý múi document types khác nhau
- ✅ Dễ deploy (chỉ cần thay .env)
- ✅ Dễ debug (thay đổi config mà không cần code)
- ✅ Dễ test (mock config)
- ✅ Production-ready

