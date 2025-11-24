"""
Convert documents to HTML format with proper styling and structure.
Supports: Markdown → HTML, CSV → HTML Table, DOCX → HTML
"""

import csv
from io import StringIO
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    logger.warning("markdown not available")
    MARKDOWN_AVAILABLE = False


class HtmlConverter:
    """Convert various formats to HTML."""

    def __init__(self):
        """Initialize HTML converter."""
        pass

    def markdown_to_html(
        self,
        markdown_content: str,
        metadata: Optional[Dict[str, Any]] = None,
        include_toc: bool = False
    ) -> str:
        """
        Convert markdown content to HTML.

        Args:
            markdown_content: Markdown text content
            metadata: Optional metadata for HTML header (title, author, etc.)
            include_toc: Whether to include table of contents

        Returns:
            Complete HTML document as string
        """
        if not MARKDOWN_AVAILABLE:
            raise RuntimeError("markdown library not installed. Install with: pip install markdown")

        logger.info("Converting markdown to HTML...")

        # Configure extensions for markdown
        extensions = [
            'tables',           # Support for markdown tables
            'fenced_code',      # Code blocks with ``` ```
            'nl2br',            # Convert newlines to <br>
            'extra',            # Extra features (abbreviations, footnotes)
        ]

        if include_toc:
            extensions.append('toc')  # Table of contents

        # Convert markdown to HTML
        html_body = markdown.markdown(
            markdown_content,
            extensions=extensions,
            extension_configs={
                'toc': {
                    'permalink': True,
                    'title': 'Mục lục',
                }
            }
        )

        # Wrap in complete HTML document
        full_html = self._wrap_in_html_document(html_body, metadata)

        logger.info(f"Successfully converted markdown to HTML ({len(full_html)} bytes)")
        return full_html

    def csv_to_html(self, csv_content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert CSV content to HTML table.

        Args:
            csv_content: CSV text content
            metadata: Optional metadata

        Returns:
            Complete HTML document with table
        """
        logger.info("Converting CSV to HTML...")

        try:
            reader = csv.reader(StringIO(csv_content))
            rows = list(reader)

            if not rows:
                raise ValueError("CSV is empty")

            # Build HTML table
            html_table = '<table class="csv-table">\n'

            # Header row
            html_table += '<thead>\n<tr>\n'
            for cell in rows[0]:
                html_table += f'  <th>{self._escape_html(cell.strip())}</th>\n'
            html_table += '</tr>\n</thead>\n'

            # Data rows
            html_table += '<tbody>\n'
            for row in rows[1:]:
                html_table += '<tr>\n'
                for cell in row:
                    html_table += f'  <td>{self._escape_html(cell.strip())}</td>\n'
                html_table += '</tr>\n'
            html_table += '</tbody>\n'

            html_table += '</table>'

            # Wrap in HTML document
            full_html = self._wrap_in_html_document(html_table, metadata)

            logger.info(f"Successfully converted CSV to HTML ({len(full_html)} bytes, {len(rows)} rows)")
            return full_html

        except Exception as e:
            logger.error(f"Error converting CSV: {e}")
            raise

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _wrap_in_html_document(
        self,
        html_body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Wrap HTML body in complete HTML document structure.

        Args:
            html_body: HTML body content
            metadata: Optional metadata (title, author, description, etc.)

        Returns:
            Complete HTML document
        """
        # Extract metadata
        title = "Document"
        author = ""
        description = ""

        if metadata:
            title = metadata.get("title", "Document")
            author = metadata.get("author", "")
            description = metadata.get("description", "")

        # Build author/date meta tags
        author_meta = f'<meta name="author" content="{self._escape_html(author)}">\n' if author else ""
        description_meta = (
            f'<meta name="description" content="{self._escape_html(description)}">\n'
            if description
            else ""
        )

        # CSS styling
        css = """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: white;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }

        header {
            border-bottom: 3px solid #2c3e50;
            margin-bottom: 40px;
            padding-bottom: 20px;
        }

        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }

        h2 {
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 15px;
            font-size: 1.8em;
            border-left: 5px solid #3498db;
            padding-left: 15px;
        }

        h3 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 12px;
            font-size: 1.3em;
        }

        h4, h5, h6 {
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        p {
            margin-bottom: 15px;
            text-align: justify;
        }

        ul, ol {
            margin-left: 30px;
            margin-bottom: 15px;
        }

        li {
            margin-bottom: 8px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            background-color: #fff;
        }

        table.csv-table {
            border: 1px solid #ddd;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 12px 15px;
            text-align: left;
        }

        th {
            background-color: #34495e;
            color: white;
            font-weight: bold;
        }

        tr:nth-child(even) {
            background-color: #f9f9f9;
        }

        tr:hover {
            background-color: #f0f0f0;
        }

        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            color: #d63384;
        }

        pre {
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 20px 0;
            font-family: 'Courier New', monospace;
        }

        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
        }

        blockquote {
            border-left: 5px solid #3498db;
            padding-left: 20px;
            margin: 20px 0;
            color: #666;
            font-style: italic;
        }

        a {
            color: #3498db;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        hr {
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }

        .toc {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }

        .toc ul {
            margin-left: 20px;
        }

        .toc a {
            color: #2c3e50;
        }

        footer {
            border-top: 2px solid #ecf0f1;
            margin-top: 40px;
            padding-top: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }

        @media (max-width: 768px) {
            .container {
                padding: 20px 10px;
            }

            h1 {
                font-size: 1.8em;
            }

            h2 {
                font-size: 1.4em;
            }

            table {
                font-size: 0.9em;
            }

            th, td {
                padding: 8px 10px;
            }
        }

        @media print {
            body {
                background-color: white;
            }

            .container {
                box-shadow: none;
                max-width: 100%;
                padding: 0;
            }

            a {
                color: #2c3e50;
            }
        }
        """

        html_document = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>{self._escape_html(title)}</title>
    {author_meta}{description_meta}<style>
{css}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{self._escape_html(title)}</h1>
            {f'<p><strong>Tác giả:</strong> {self._escape_html(author)}</p>' if author else ''}
        </header>

        <main>
{html_body}
        </main>

        <footer>
            <p>Tạo bởi Document Conversion API | Generated on {self._get_timestamp()}</p>
        </footer>
    </div>
</body>
</html>"""

        return html_document

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
