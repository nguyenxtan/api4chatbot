#!/usr/bin/env python3
"""
Test script for markdown to bullet conversion
"""

import sys
sys.path.insert(0, '/Users/tannx/Documents/chatbot/api4chatbot')

from src.core.markdown_to_bullet import MarkdownToBulletConverter

# Test markdown content (from sample)
test_markdown = """### BẢNG 02 - TÁC NGHIỆP TẠI BÃI ĐỐI VỚI CONTAINER HÀNG THÔNG THƯỜNG

• Đơn vị tính: đồng/container

| TT | Phương án | 20' khô | 40' khô | 45' khô | 20' lạnh | 40'/45' lạnh |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Xe → Bãi | 497.000 | 882.000 | 1.031.000 | 646.000 | 1.136.000 |
| 2 | Hạ container ở tầng trên xuống đất phục vụ kiểm hoá | 298.000 | 528.000 | 627.000 | 596.000 | 1.018.000 |
| 3 | Hạ container xuất từ xe xuống đất phục vụ kiểm hoá | 795.000 | 1.410.000 | 1.658.000 | 1.242.000 | 2.155.000 |

Ghi chú: Cước đảo chuyển sẽ được thu bổ sung theo quy định tại Bảng 23-TT.9."""

# Create converter
converter = MarkdownToBulletConverter()

# Convert
result = converter.convert(test_markdown)

# Print result
print("=" * 80)
print("CONVERTED OUTPUT:")
print("=" * 80)
print(result)
print("=" * 80)
print("\nExpected output format:")
print("=" * 80)

expected = """BẢNG 02 - TÁC NGHIỆP TẠI BÃI ĐỐI VỚI CONTAINER HÀNG THÔNG THƯỜNG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Đơn vị tính: đồng/container

┃ PHƯƠNG ÁN 1: Xe xuống bãi
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ • 20' khô              → 497.000
┃ • 40' khô              → 882.000
┃ • 45' khô              → 1.031.000
┃ • 20' lạnh             → 646.000
┃ • 40'/45' lạnh         → 1.136.000

┃ PHƯƠNG ÁN 2: Hạ container ở tầng trên xuống đất phục vụ kiểm hoá
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ • 20' khô              → 298.000
┃ • 40' khô              → 528.000
┃ • 45' khô              → 627.000
┃ • 20' lạnh             → 596.000
┃ • 40'/45' lạnh         → 1.018.000
┃ ⓘ Ghi chú: Cước đảo chuyển sẽ được thu bổ sung theo quy định tại Bảng 23-TT.9

┃ PHƯƠNG ÁN 3: Hạ container xuất từ xe xuống đất phục vụ kiểm hoá
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ • 20' khô              → 795.000
┃ • 40' khô              → 1.410.000
┃ • 45' khô              → 1.658.000
┃ • 20' lạnh             → 1.242.000
┃ • 40'/45' lạnh         → 2.155.000"""

print(expected)
