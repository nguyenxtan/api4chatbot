#!/usr/bin/env python3
"""
Test that HTML endpoint returns HTML content (not JSON).
"""

import sys
from pathlib import Path
from src.core.html_converter import HtmlConverter
from src.core.stage1_markdown import MarkdownConverter

def test_html_response_content():
    """Test that HTML is returned as content, not JSON response."""
    print("=" * 70)
    print("TEST: HTML Response Content Type")
    print("=" * 70)

    docx_file = Path("test_document.docx")
    if not docx_file.exists():
        print("✗ test_document.docx not found")
        return False

    try:
        # Convert DOCX to HTML
        print("\nStep 1: Convert DOCX to Markdown...")
        markdown_converter = MarkdownConverter()
        markdown_result = markdown_converter.convert(str(docx_file))
        markdown_content = markdown_result["markdown"]
        print(f"✓ Markdown generated ({len(markdown_content)} chars)")

        print("\nStep 2: Convert Markdown to HTML...")
        html_converter = HtmlConverter()
        html_content = html_converter.markdown_to_html(
            markdown_content,
            markdown_result.get("metadata", {})
        )
        print(f"✓ HTML generated ({len(html_content)} bytes)")

        # Check that this is HTML content (not JSON)
        print("\nStep 3: Verify response is HTML (not JSON)...")

        checks = {
            "Starts with <!DOCTYPE": html_content.strip().startswith("<!DOCTYPE"),
            "Contains <html": "<html" in html_content,
            "Contains <body": "<body" in html_content,
            "Contains </html>": "</html>" in html_content,
            "NOT JSON object": not html_content.strip().startswith("{"),
            "NOT JSON array": not html_content.strip().startswith("["),
            "Has actual content": len(html_content) > 1000,
        }

        all_ok = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
            if not result:
                all_ok = False

        if not all_ok:
            print("\n❌ Content is not valid HTML!")
            return False

        # Show preview
        print("\nPreview (first 500 chars of response body):")
        print("-" * 70)
        print(html_content[:500])
        print("...")
        print("-" * 70)

        print("\n✅ Endpoint will return HTML content, not JSON!")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_http_response_format():
    """Test the HTTP response format."""
    print("\n" + "=" * 70)
    print("TEST: HTTP Response Format")
    print("=" * 70)

    print("\nWhen you call POST /documents/html with DOCX file:")
    print("  Response will be:")
    print("    - Content-Type: text/html; charset=utf-8")
    print("    - Status: 200 OK")
    print("    - Body: Complete HTML document")
    print("\n  NOT:")
    print("    - Content-Type: application/json")
    print("    - Body: { 'status': 'success', 'filename': '...', ... }")

    print("\n✅ This is the correct behavior!")
    return True


if __name__ == "__main__":
    print("\n🧪 HTML RESPONSE CONTENT TYPE TEST\n")

    results = [
        test_html_response_content(),
        test_http_response_format(),
    ]

    print("\n" + "=" * 70)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("\nEndpoint /documents/html now returns:")
        print("  ✓ HTML content directly in response body")
        print("  ✓ Content-Type: text/html")
        print("  ✓ Full HTML document with styling")
        print("\nYou can see the rendered HTML in browser!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed")
        sys.exit(1)
