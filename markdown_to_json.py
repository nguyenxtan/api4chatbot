#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để chuyển đổi file markdown thành JSON
Trích xuất các bảng cùng với tiêu đề mục phân cấp
"""

import re
import json


def parse_markdown_to_json(input_file, output_file):
    """
    Đọc file markdown và chuyển đổi thành JSON

    Args:
        input_file: Đường dẫn đến file markdown input
        output_file: Đường dẫn đến file JSON output
    """

    # Đọc toàn bộ nội dung file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    # Danh sách kết quả
    result = []

    # Tracking heading hierarchy
    heading_stack = {
        'muc_chinh': None,
        'muc_cap_1': None,
        'muc_cap_2': None,
        'muc_cap_3': None,
        'muc_cap_4': None
    }

    current_table_name = None
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Kiểm tra heading (###)
        if line.startswith('###'):
            heading_text = line.replace('###', '').strip()

            # Xác định loại heading
            # Mục chính: số La Mã (II., III., IV., etc.)
            if re.match(r'^[IVX]+\.', heading_text):
                heading_stack['muc_chinh'] = heading_text
                heading_stack['muc_cap_1'] = None
                heading_stack['muc_cap_2'] = None
                heading_stack['muc_cap_3'] = None
                heading_stack['muc_cap_4'] = None

            # Mục cấp 1: số đơn (1., 2., 3., etc.)
            elif re.match(r'^\d+\.\s+', heading_text):
                heading_stack['muc_cap_1'] = heading_text
                heading_stack['muc_cap_2'] = None
                heading_stack['muc_cap_3'] = None
                heading_stack['muc_cap_4'] = None

            # Mục cấp 2: số thập phân cấp 1 (1.1., 2.3., etc.)
            elif re.match(r'^\d+\.\d+\.\s+', heading_text):
                heading_stack['muc_cap_2'] = heading_text
                heading_stack['muc_cap_3'] = None
                heading_stack['muc_cap_4'] = None

            # Mục cấp 3: số thập phân cấp 2 (1.1.1., 2.3.4., etc.)
            elif re.match(r'^\d+\.\d+\.\d+\.\s+', heading_text):
                heading_stack['muc_cap_3'] = heading_text
                heading_stack['muc_cap_4'] = None

            # Mục cấp 4: ký tự (a., b., c., etc.)
            elif re.match(r'^[a-z]\.\s+', heading_text):
                heading_stack['muc_cap_4'] = heading_text

            # Tên bảng (Bảng XX)
            elif re.match(r'^Bảng\s+\d+', heading_text, re.IGNORECASE):
                current_table_name = heading_text

        # Kiểm tra bảng (bắt đầu bằng |)
        elif line.startswith('|') and current_table_name:
            # Thu thập toàn bộ bảng
            table_lines = []
            j = i

            while j < len(lines):
                line_j = lines[j].strip()

                if line_j.startswith('|'):
                    table_lines.append(lines[j])
                    j += 1
                elif j + 1 < len(lines) and lines[j + 1].strip().startswith('|'):
                    # Bỏ qua dòng rác, tiếp tục nếu dòng sau vẫn là bảng
                    j += 1
                else:
                    # Kết thúc bảng
                    break

            # Tạo object JSON cho bảng này
            table_object = {
                "ten_bang": current_table_name,
                "tieu_de_muc": {
                    "muc_chinh": heading_stack['muc_chinh'],
                    "muc_cap_1": heading_stack['muc_cap_1'],
                    "muc_cap_2": heading_stack['muc_cap_2'],
                    "muc_cap_3": heading_stack['muc_cap_3'],
                    "muc_cap_4": heading_stack['muc_cap_4']
                },
                "noi_dung_bang": '\n'.join(table_lines)
            }

            result.append(table_object)

            # Reset tên bảng và nhảy đến vị trí sau bảng
            current_table_name = None
            i = j - 1

        i += 1

    # Ghi kết quả ra file JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print(f"✅ Đã chuyển đổi thành công!")
    print(f"📄 Input: {input_file}")
    print(f"📄 Output: {output_file}")
    print(f"📊 Tổng số bảng: {len(result)}")


if __name__ == "__main__":
    # Sử dụng script
    input_file = "input.md"
    output_file = "output.json"

    try:
        parse_markdown_to_json(input_file, output_file)
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file: {input_file}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
