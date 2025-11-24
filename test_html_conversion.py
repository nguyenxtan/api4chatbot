#!/usr/bin/env python3
"""
Test HTML conversion functionality.
"""

import sys
from pathlib import Path

def test_html_converter_module():
    """Test that HTML converter module exists and imports correctly."""
    print("=" * 70)
    print("TEST 1: HTML Converter Module")
    print("=" * 70)

    try:
        from src.core.html_converter import HtmlConverter
        print("✓ HtmlConverter imported successfully")

        converter = HtmlConverter()
        print("✓ HtmlConverter instantiated")

        # Test markdown to HTML
        test_markdown = """# Test Document

## Section 1

This is a **test** document.

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

### Subsection
- Item 1
- Item 2
- Item 3
"""

        html = converter.markdown_to_html(test_markdown)
        assert "<html" in html.lower(), "HTML document not generated"
        assert "<h1>Test Document</h1>" in html, "Header not found"
        assert "<table" in html, "Table not found"
        print("✓ Markdown to HTML conversion works")

        # Test CSV to HTML
        test_csv = """Name,Age,City
John,30,New York
Jane,25,London
Bob,35,Paris"""

        html_table = converter.csv_to_html(test_csv)
        assert "<table" in html_table, "Table not generated"
        assert "John" in html_table, "CSV data not found"
        print("✓ CSV to HTML conversion works")

        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_endpoint():
    """Test that HTML endpoint is properly configured in API."""
    print("\n" + "=" * 70)
    print("TEST 2: HTML Endpoint Configuration")
    print("=" * 70)

    try:
        api_file = Path("src/api.py")
        with open(api_file, "r") as f:
            content = f.read()

        # Check for HTML endpoint
        if "@app.post(\"/documents/html\")" not in content:
            print("✗ HTML endpoint not found")
            return False
        print("✓ HTML endpoint declared")

        # Check for HtmlConverter import
        if "from src.core.html_converter import HtmlConverter" not in content:
            print("✗ HtmlConverter not imported")
            return False
        print("✓ HtmlConverter imported in API")

        # Check for html_converter initialization
        if "html_converter = HtmlConverter()" not in content:
            print("✗ HtmlConverter not initialized")
            return False
        print("✓ HtmlConverter initialized")

        # Check for CSV handling
        if ".csv" not in content or "csv_to_html" not in content:
            print("✗ CSV handling not found")
            return False
        print("✓ CSV conversion implemented")

        # Check for file type validation
        if "allowed_extensions = {" not in content or ".docx" not in content:
            print("✗ File type validation unclear")
            return False
        print("✓ File type validation present")

        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_html_response_format():
    """Test that HTML response format is correct."""
    print("\n" + "=" * 70)
    print("TEST 3: HTML Response Format")
    print("=" * 70)

    try:
        from src.core.html_converter import HtmlConverter

        converter = HtmlConverter()

        test_markdown = "# Test\n\nContent here."
        metadata = {
            "title": "My Document",
            "author": "John Doe",
            "description": "Test document"
        }

        html = converter.markdown_to_html(test_markdown, metadata)

        # Check response structure
        checks = {
            "DOCTYPE": "<!DOCTYPE html>" in html,
            "HTML tag": "<html" in html,
            "Head tag": "<head>" in html,
            "Meta charset": "UTF-8" in html,
            "Title tag": "<title>" in html,
            "Body tag": "<body>" in html,
            "Container div": 'class="container"' in html,
            "Header element": "<header>" in html,
            "Main element": "<main>" in html,
            "Footer element": "<footer>" in html,
            "Metadata author": "John Doe" in html,
            "Metadata title": "My Document" in html,
        }

        all_passed = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"{status} {check_name}")
            if not result:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_csv_to_html():
    """Test CSV to HTML conversion."""
    print("\n" + "=" * 70)
    print("TEST 4: CSV to HTML Conversion")
    print("=" * 70)

    try:
        from src.core.html_converter import HtmlConverter

        converter = HtmlConverter()

        # Test with simple CSV
        csv_content = """Product,Price,Quantity
Apple,1.00,10
Banana,0.50,20
Orange,2.00,5"""

        html = converter.csv_to_html(csv_content)

        checks = {
            "Table element": "<table" in html,
            "Header row": "<thead>" in html,
            "Body row": "<tbody>" in html,
            "Product header": "Product" in html,
            "Price header": "Price" in html,
            "Apple data": "Apple" in html,
            "1.00 data": "1.00" in html,
        }

        all_passed = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"{status} {check_name}")
            if not result:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 HTML CONVERSION FEATURE TESTS\n")

    results = [
        test_html_converter_module(),
        test_html_endpoint(),
        test_html_response_format(),
        test_csv_to_html(),
    ]

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n✅ ALL TESTS PASSED - HTML conversion feature is ready!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed")
        sys.exit(1)
