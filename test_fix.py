#!/usr/bin/env python3
"""
Test script to verify the critical hardcode fix.
Verifies that the reference markdown bypass has been removed.
"""

import sys
from pathlib import Path

def test_no_reference_markdown_bypass():
    """
    Verify that src/api.py no longer contains the reference markdown bypass logic.
    """
    api_file = Path("src/api.py")

    with open(api_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Check that the problematic code is removed
    dangerous_patterns = [
        'reference_markdown_path = Path("sample") / "markdown.md"',
        'if reference_markdown_path.exists()',
        'markdown_source = "reference"',
        'Using reference markdown'
    ]

    print("=" * 70)
    print("VERIFICATION: Reference Markdown Bypass Removal")
    print("=" * 70)

    found_issues = []
    for pattern in dangerous_patterns:
        if pattern in content:
            found_issues.append(pattern)
            print(f"✗ FOUND: {pattern}")
        else:
            print(f"✓ OK: {pattern} (removed)")

    # Verify that conversion always happens
    good_patterns = [
        "# Convert to markdown from file",
        'logger.info("Converting file to markdown...")',
        'markdown_result = markdown_converter.convert(str(file_to_convert))',
        '"markdown_source": "extracted"'
    ]

    print("\nVerifying correct conversion logic is present:")
    for pattern in good_patterns:
        if pattern in content:
            print(f"✓ OK: {pattern}")
        else:
            print(f"✗ MISSING: {pattern}")
            found_issues.append(f"Missing: {pattern}")

    print("\n" + "=" * 70)

    if found_issues:
        print("❌ FAILED: Critical hardcode still present!")
        for issue in found_issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ PASSED: Reference markdown bypass has been properly removed")
        print("\nBenefit: API will now correctly process uploaded files")
        print("instead of returning hardcoded reference markdown.")
        return True

if __name__ == "__main__":
    try:
        success = test_no_reference_markdown_bypass()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Test error: {e}")
        sys.exit(1)
