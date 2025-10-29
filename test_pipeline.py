#!/usr/bin/env python3
"""
End-to-end test script: cleanfile -> markdown -> bullet
Tests the complete pipeline with PDF sample data.
"""
import sys
from pathlib import Path
from loguru import logger

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.file_cleaner import FileCleaner
from src.core.stage1_markdown import MarkdownConverter
from src.core.markdown_to_bullet import MarkdownToBulletConverter

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<level>{level: <8}</level> | {message}")


def test_pipeline():
    """Test complete pipeline: cleanfile -> markdown -> bullet"""

    # Sample PDF file
    pdf_file = PROJECT_ROOT / "sample" / "508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf"

    if not pdf_file.exists():
        logger.error(f"Sample PDF not found: {pdf_file}")
        return False

    logger.info(f"Starting pipeline test with: {pdf_file.name}")

    # Stage 1: Clean file
    logger.info("=" * 80)
    logger.info("Stage 1: Cleaning file...")
    logger.info("=" * 80)

    file_cleaner = FileCleaner()
    success, message, cleaned_path = file_cleaner.clean_file(str(pdf_file))

    if not success:
        logger.error(f"File cleaning failed: {message}")
        return False

    logger.info(f"✓ File cleaned successfully: {cleaned_path}")

    # Stage 2: Convert to markdown
    logger.info("=" * 80)
    logger.info("Stage 2: Converting cleaned file to markdown...")
    logger.info("=" * 80)

    markdown_converter = MarkdownConverter()
    try:
        markdown_result = markdown_converter.convert(cleaned_path)
        markdown_content = markdown_result["markdown"]
        logger.info(f"✓ Converted to markdown ({len(markdown_content)} characters)")

        # Save markdown for inspection
        temp_markdown = PROJECT_ROOT / "temp" / "debug_markdown.md"
        temp_markdown.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_markdown, "w", encoding="utf-8") as f:
            f.write(markdown_content)
    except Exception as e:
        logger.error(f"Markdown conversion failed: {e}")
        return False

    # Stage 3: Convert to bullet format
    logger.info("=" * 80)
    logger.info("Stage 3: Converting markdown to bullet format...")
    logger.info("=" * 80)

    bullet_converter = MarkdownToBulletConverter()
    try:
        bullet_content = bullet_converter.convert(markdown_content)
        logger.info(f"✓ Converted to bullet format ({len(bullet_content)} characters)")
    except Exception as e:
        logger.error(f"Bullet conversion failed: {e}")
        return False

    # Stage 4: Save output as bullet.md
    logger.info("=" * 80)
    logger.info("Stage 4: Saving output to sample/bullet.md...")
    logger.info("=" * 80)

    output_file = PROJECT_ROOT / "sample" / "bullet.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(bullet_content)
        logger.info(f"✓ Output saved to: {output_file}")
        logger.info(f"✓ File size: {output_file.stat().st_size} bytes")
    except Exception as e:
        logger.error(f"Failed to save bullet.md: {e}")
        return False

    # Final summary
    logger.info("=" * 80)
    logger.info("✓ PIPELINE TEST PASSED")
    logger.info("=" * 80)
    logger.info(f"Output file: {output_file}")
    logger.info(f"Output size: {len(bullet_content)} characters")
    logger.info("\nTo view the result:")
    logger.info(f"  cat {output_file}")

    return True


if __name__ == "__main__":
    try:
        success = test_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
