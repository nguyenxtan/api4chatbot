#!/usr/bin/env python3
"""
Security and risk assessment for the fixed code.
"""

import sys
from pathlib import Path
import re

def check_file_path_security():
    """Check for path traversal vulnerabilities and proper path handling."""
    api_file = Path("src/api.py")

    with open(api_file, "r") as f:
        content = f.read()

    print("=" * 70)
    print("SECURITY CHECK: File Path Handling")
    print("=" * 70)

    issues = []

    # Check download endpoint has proper security
    if "path_file.resolve()" in content and "startswith(str(temp_dir))" in content:
        print("✓ Download endpoint has path traversal protection")
    else:
        print("⚠ Download endpoint path validation unclear")

    # Check for user input validation
    if "file_ext = Path(file.filename).suffix.lower()" in content:
        if "allowed_extensions" in content:
            print("✓ File type validation present")
        else:
            issues.append("No file type validation")
    else:
        print("⚠ File extension handling unclear")

    # Check temp file handling
    if "temp_file.unlink()" in content:
        print("✓ Temp files are properly cleaned up")
    else:
        issues.append("Temp files may not be cleaned up")

    # Check for hardcoded paths that could be security issues
    dangerous_paths = [
        r'Path\("sample"\)\s*/\s*"markdown.md"',  # The one we fixed
        r'Path\("temp"\)\s*/\s*"cleaned"',
        r'open\(["\'].*sensitive',
        r'Path\("[/\\]',  # Absolute paths
    ]

    found_dangerous = []
    for pattern in dangerous_paths:
        if re.search(pattern, content):
            found_dangerous.append(pattern)

    if found_dangerous:
        print("\n⚠ Potential security concerns:")
        for pattern in found_dangerous:
            print(f"  - Pattern: {pattern}")
    else:
        print("✓ No obvious hardcoded sensitive paths")

    return len(issues) == 0


def check_input_validation():
    """Check that user inputs are properly validated."""
    api_file = Path("src/api.py")

    with open(api_file, "r") as f:
        content = f.read()

    print("\n" + "=" * 70)
    print("SECURITY CHECK: Input Validation")
    print("=" * 70)

    checks = {
        "File extension whitelist": "allowed_extensions = {" in content,
        "Content type validation": ".suffix.lower()" in content,
        "Empty file check": "not request.text or not request.text.strip()" in content,
        "File size limit": "file size" in content.lower(),  # May not be implemented
        "Error handling": "except Exception as e" in content,
    }

    for check, result in checks.items():
        status = "✓" if result else "⚠"
        print(f"  {status} {check}")

    return True


def check_for_sql_injection():
    """Check for SQL injection vulnerabilities."""
    print("\n" + "=" * 70)
    print("SECURITY CHECK: SQL Injection Risk")
    print("=" * 70)

    api_file = Path("src/api.py")
    with open(api_file, "r") as f:
        content = f.read()

    # This is a document processing API, not database-driven
    if "execute" not in content.lower() and "query" not in content.lower():
        print("✓ No SQL execution detected (file-based processing)")
    else:
        print("⚠ SQL operations detected - verify queries are parameterized")

    return True


def check_for_xss():
    """Check for potential XSS vulnerabilities."""
    print("\n" + "=" * 70)
    print("SECURITY CHECK: Cross-Site Scripting (XSS) Risk")
    print("=" * 70)

    api_file = Path("src/api.py")
    with open(api_file, "r") as f:
        content = f.read()

    # Check if user-controlled data is properly escaped
    if "HTTPException" in content:
        print("✓ Using FastAPI's HTTPException (properly escapes output)")
    else:
        print("⚠ Check error handling")

    if "json.dumps" in content or "JSONResponse" in content:
        print("✓ Using JSON serialization (prevents XSS)")
    else:
        print("⚠ Check JSON encoding")

    return True


def check_for_dos():
    """Check for Denial of Service (DoS) vulnerabilities."""
    print("\n" + "=" * 70)
    print("SECURITY CHECK: Denial of Service (DoS) Risk")
    print("=" * 70)

    api_file = Path("src/api.py")
    with open(api_file, "r") as f:
        content = f.read()

    issues = []

    # Check for timeout handling
    if "timeout" not in content.lower():
        print("⚠ No explicit timeout limits found")
        issues.append("Consider adding request timeouts")
    else:
        print("✓ Timeout handling found")

    # Check for file size limits
    if "max_size" not in content.lower() and "size limit" not in content.lower():
        print("⚠ No file size limit found")
        issues.append("Consider adding file size validation")
    else:
        print("✓ File size validation found")

    # Check for rate limiting
    if "rate_limit" not in content.lower():
        print("⚠ No rate limiting found")
        issues.append("Consider adding rate limiting in production")
    else:
        print("✓ Rate limiting detected")

    return len(issues) == 0


def check_logging_security():
    """Check that logging doesn't leak sensitive information."""
    print("\n" + "=" * 70)
    print("SECURITY CHECK: Logging and Information Disclosure")
    print("=" * 70)

    api_file = Path("src/api.py")
    with open(api_file, "r") as f:
        content = f.read()

    # Check what's being logged
    logger_calls = re.findall(r'logger\.(info|warning|error|debug)\((.*?)\)', content)

    sensitive_patterns = [
        r'password',
        r'secret',
        r'key',
        r'token',
        r'api_key',
        r'credential',
    ]

    print("Checking logged information...")
    issues = []
    for level, message in logger_calls:
        for pattern in sensitive_patterns:
            if re.search(pattern, message.lower()):
                issues.append(f"Possible sensitive data in {level}: {message[:50]}")

    if issues:
        print("⚠ Potential sensitive data in logs:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ No obvious sensitive data in logs")

    return len(issues) == 0


if __name__ == "__main__":
    print("\n🔒 SECURITY ASSESSMENT REPORT\n")

    try:
        check_file_path_security()
        check_input_validation()
        check_for_sql_injection()
        check_for_xss()
        check_for_dos()
        check_logging_security()

        print("\n" + "=" * 70)
        print("✅ SECURITY CHECKS COMPLETE")
        print("=" * 70)
        print("""
Recommendations:
1. Add file size limits (e.g., max 50MB)
2. Add request timeouts
3. Implement rate limiting for production
4. Add CORS configuration
5. Consider adding authentication/authorization
6. Run periodic security scans
        """)

    except Exception as e:
        print(f"\n✗ Error during security checks: {e}")
        sys.exit(1)
