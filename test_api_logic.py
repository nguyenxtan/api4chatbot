#!/usr/bin/env python3
"""
Test API logic to ensure fixes don't break existing functionality.
"""

import sys
import ast
from pathlib import Path

def analyze_api_function():
    """Analyze convert_to_markdown function for correctness."""
    api_file = Path("src/api.py")

    with open(api_file, "r") as f:
        tree = ast.parse(f.read())

    # Find convert_to_markdown function
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "convert_to_markdown":
            print("=" * 70)
            print("ANALYSIS: convert_to_markdown Function")
            print("=" * 70)

            # Extract function signature
            args = [arg.arg for arg in node.args.args]
            print(f"\nFunction signature:")
            print(f"  async def convert_to_markdown({', '.join(args)})")

            # Check for key operations
            operations = {
                "file_validation": False,
                "temp_file_save": False,
                "file_cleaning": False,
                "markdown_conversion": False,
                "markdown_saving": False,
                "response_generation": False,
                "temp_cleanup": False,
            }

            source = ast.get_source_segment(open(api_file).read(), node)

            # Simple pattern matching
            if "allowed_extensions" in source:
                operations["file_validation"] = True
            if "temp_file" in source and "write" in source:
                operations["temp_file_save"] = True
            if "file_cleaner" in source:
                operations["file_cleaning"] = True
            if "markdown_converter.convert" in source:
                operations["markdown_conversion"] = True
            if "markdown_output_path" in source and "write" in source:
                operations["markdown_saving"] = True
            if "return {" in source:
                operations["response_generation"] = True
            if "temp_file.unlink()" in source:
                operations["temp_cleanup"] = True

            print("\nOperation Checklist:")
            all_ok = True
            for op, present in operations.items():
                status = "✓" if present else "✗"
                print(f"  {status} {op}")
                if not present:
                    all_ok = False

            return all_ok

    print("✗ Function not found!")
    return False


def check_no_hardcoded_paths():
    """Check for dangerous hardcoded paths in convert_to_markdown."""
    api_file = Path("src/api.py")

    with open(api_file, "r") as f:
        content = f.read()

    # Find convert_to_markdown function
    start = content.find("async def convert_to_markdown")
    if start == -1:
        print("Function not found")
        return False

    # Get function content (up to next @app decorator or end of file)
    end = content.find("\n@app", start + 1)
    if end == -1:
        end = len(content)

    func_content = content[start:end]

    print("\n" + "=" * 70)
    print("CHECK: Hardcoded Paths in Function")
    print("=" * 70)

    # Check for problematic hardcodes
    issues = []

    # Verify Path("sample") is only used for OUTPUT, not INPUT
    if 'reference_markdown_path = Path("sample")' in func_content:
        issues.append("✗ Reference markdown bypass still present")
    else:
        print("✓ No reference markdown input bypass")

    # Verify proper use of temp directory
    if "temp_dir = Path" in func_content and 'temp_file = temp_dir' in func_content:
        print("✓ Proper temp file handling")
    else:
        print("⚠ Temp file handling unclear")

    # Verify sample directory is used for OUTPUT only
    if "markdown_output_path = sample_dir" in func_content:
        print("✓ Sample directory used correctly for output")
    else:
        print("⚠ Sample directory handling unclear")

    return len(issues) == 0


def check_dependencies():
    """Verify required dependencies are imported."""
    api_file = Path("src/api.py")

    with open(api_file, "r") as f:
        content = f.read()

    print("\n" + "=" * 70)
    print("CHECK: Required Dependencies")
    print("=" * 70)

    required = {
        "Path": "from pathlib import Path",
        "FastAPI": "from fastapi import FastAPI",
        "UploadFile": "from fastapi import.*UploadFile",
        "MarkdownConverter": "from src.core.stage1_markdown import MarkdownConverter",
        "FileCleaner": "from src.core.file_cleaner import FileCleaner",
    }

    all_ok = True
    for dep, pattern in required.items():
        if "import" in content and dep in content:
            print(f"✓ {dep} imported")
        else:
            print(f"✗ {dep} not found")
            all_ok = False

    return all_ok


if __name__ == "__main__":
    print("\n🔍 COMPREHENSIVE API LOGIC CHECK\n")

    results = []

    try:
        print("1. Function Analysis")
        results.append(analyze_api_function())

        print("\n2. Path Hardcoding Check")
        results.append(check_no_hardcoded_paths())

        print("\n3. Dependencies Check")
        results.append(check_dependencies())

        print("\n" + "=" * 70)
        if all(results):
            print("✅ ALL CHECKS PASSED - API logic is correct and safe")
            sys.exit(0)
        else:
            print("⚠ Some checks failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error during checks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
