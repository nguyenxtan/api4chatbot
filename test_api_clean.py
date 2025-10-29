"""Test API cleanfile endpoint"""
import sys
sys.path.insert(0, '.')

from src.core.file_cleaner import FileCleaner
from pathlib import Path

# Test direct
print("="*80)
print("TESTING: Direct FileCleaner")
print("="*80)

cleaner = FileCleaner()
success, message, output = cleaner.clean_file('sample/508_QĐ_TCg_Quyết_định_về_việc_ban_hành_Biểu_giá_dịch.pdf')

print(f"\nSuccess: {success}")
print(f"Message: {message}")
print(f"Output: {output}")

# Check result
if output:
    import pikepdf
    with pikepdf.open(output) as pdf:
        page1 = pdf.pages[0]
        contents = page1['/Contents']
        if isinstance(contents, pikepdf.Array):
            streams = list(contents)
        else:
            streams = [contents]
        
        print(f"\nResult:")
        print(f"  Streams: {len(streams)}")
        
        for i, s in enumerate(streams):
            ops = len([l for l in s.read_bytes().decode('latin-1', errors='ignore').split('\n') if l.strip().endswith(('Tj', 'TJ'))])
            print(f"  Stream {i}: {ops} text operators")

print("\n" + "="*80)
print("API đang chạy bản: c3b9347 (with hex footer removal)")
print("="*80)
