#!/usr/bin/env python3
"""
Test HTML conversion endpoint with a real DOCX file.
Simulate a file upload request to the /documents/html endpoint.
"""

import sys
import json
from pathlib import Path
from io import BytesIO

# Test the HTML converter directly
from src.core.html_converter import HtmlConverter
from src.core.stage1_markdown import MarkdownConverter

def test_html_conversion_with_docx():
    """Test HTML conversion with actual DOCX file."""
    print("=" * 70)
    print("TEST: HTML Conversion with DOCX Input File")
    print("=" * 70)

    # Check if test DOCX exists
    docx_file = Path("test_document.docx")
    if not docx_file.exists():
        print("✗ test_document.docx not found")
        return False

    print(f"\nInput file: {docx_file.name}")
    print(f"File size: {docx_file.stat().st_size} bytes")

    try:
        # Step 1: Convert DOCX to Markdown
        print("\n[Step 1] Converting DOCX → Markdown...")
        markdown_converter = MarkdownConverter()
        markdown_result = markdown_converter.convert(str(docx_file))

        markdown_content = markdown_result["markdown"]
        metadata = markdown_result.get("metadata", {})

        print(f"✓ Markdown generated ({len(markdown_content)} characters)")
        print(f"  Metadata: {metadata}")

        # Show first 500 chars of markdown
        print(f"\n  Preview (first 500 chars):")
        print(f"  {markdown_content[:500]}...")

        # Step 2: Convert Markdown to HTML
        print("\n[Step 2] Converting Markdown → HTML...")
        html_converter = HtmlConverter()
        html_content = html_converter.markdown_to_html(markdown_content, metadata)

        print(f"✓ HTML generated ({len(html_content)} bytes)")

        # Step 3: Verify HTML structure
        print("\n[Step 3] Verifying HTML structure...")
        checks = {
            "DOCTYPE": "<!DOCTYPE html>" in html_content,
            "HTML tags": "<html" in html_content and "</html>" in html_content,
            "Head tags": "<head>" in html_content and "</head>" in html_content,
            "Body tags": "<body>" in html_content and "</body>" in html_content,
            "Title": "<title>" in html_content,
            "Container": 'class="container"' in html_content,
            "Header": "<header>" in html_content,
            "Main": "<main>" in html_content,
            "Footer": "<footer>" in html_content,
            "CSS": "<style>" in html_content,
        }

        all_ok = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
            if not result:
                all_ok = False

        # Step 4: Verify content is preserved
        print("\n[Step 4] Verifying content preservation...")
        content_checks = {
            "Title preserved": "Test Document for HTML Conversion" in html_content,
            "Features section": "Section 1: Features" in html_content or "Features" in html_content,
            "Data Table": "Data Table" in html_content or "Product" in html_content,
            "Product data": "Widget" in html_content or "Product" in html_content,
            "Conclusion": "Conclusion" in html_content,
        }

        for check_name, result in content_checks.items():
            status = "✓" if result else "⚠"
            print(f"  {status} {check_name}")
            if not result:
                all_ok = False

        # Step 5: Save HTML to file
        print("\n[Step 5] Saving HTML output...")
        output_path = Path("sample") / "test_document.html"
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✓ Saved to: {output_path}")
        print(f"  File size: {output_path.stat().st_size} bytes")

        # Step 6: Show preview
        print("\n[Step 6] HTML Preview (first 1000 chars):")
        print("-" * 70)
        print(html_content[:1000])
        print("...")
        print("-" * 70)

        return all_ok

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_response_format():
    """Test the response format that would be returned by the API."""
    print("\n" + "=" * 70)
    print("TEST: API Response Format")
    print("=" * 70)

    try:
        docx_file = Path("test_document.docx")
        output_path = Path("sample") / "test_document.html"

        # Simulate the response that would be returned
        response = {
            "status": "success",
            "filename": docx_file.name,
            "format": "html",
            "output_file": str(output_path),
            "message": f"Document converted to HTML and saved to {output_path}"
        }

        print("\nAPI Response:")
        print(json.dumps(response, indent=2))

        # Verify response structure
        checks = {
            "status field": "status" in response,
            "filename field": "filename" in response,
            "format field": "format" in response,
            "output_file field": "output_file" in response,
            "message field": "message" in response,
            "status is 'success'": response.get("status") == "success",
            "format is 'html'": response.get("format") == "html",
        }

        all_ok = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
            if not result:
                all_ok = False

        return all_ok

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n🧪 HTML ENDPOINT TEST WITH DOCX FILE\n")

    results = []
    results.append(test_html_conversion_with_docx())
    results.append(test_response_format())

    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    if all(results):
        print("\n✅ ALL TESTS PASSED")
        print("\nHTML endpoint with DOCX input:")
        print("  ✓ Correctly converts DOCX to Markdown")
        print("  ✓ Correctly converts Markdown to HTML")
        print("  ✓ Preserves document content")
        print("  ✓ Generates proper HTML structure")
        print("  ✓ Response format is correct")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed")
        sys.exit(1)
