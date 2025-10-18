# 🚀 BẮT ĐẦU TẠI ĐÂY - START HERE

Chào mừng bạn đến với **Multi-Document Chunking Pipeline API**!

## ⚡ Quick Start (2 Bước)

### 1. Cài Đặt

```bash
# Cài dependencies
pip install -r requirements.txt

# Tạo thư mục
mkdir -p data/chunks logs temp
```

### 2. Khởi Động Server

```bash
python run.py
```

Server sẽ chạy tại: http://localhost:8000

---

## 📖 Tài Liệu

1. **QUICKSTART.md** - Hướng dẫn sử dụng 5 phút
2. **README.md** - Tài liệu đầy đủ
3. **API Docs** - http://localhost:8000/docs (sau khi start server)

---

## 📂 Cấu Trúc Project

```
api4chatbot/
├── 📄 START_HERE.md          ← BẠN Ở ĐÂY!
├── 📄 QUICKSTART.md          ← Đọc tiếp
├── 📄 README.md              ← Docs đầy đủ
├── 🐍 run.py                 ← Chạy server
│
├── config/schemas/           ← Document schemas (YAML)
├── src/                      ← Source code
├── tests/                    ← Test data (PDF files)
└── data/                     ← Chunk storage
```

---

## 🌐 Sử Dụng API

### Swagger UI (Giao diện web)

```bash
# Start server
python run.py

# Mở trình duyệt
http://localhost:8000/docs

# Click "Try it out" để test các endpoint
```

### Python Script

```python
import requests

# Upload document
with open("your_document.pdf", "rb") as f:
    r = requests.post(
        "http://localhost:8000/documents/process",
        files={"file": f},
        data={"document_type": "pricing"}
    )

result = r.json()
print(f"Document ID: {result['document_id']}")
print(f"Chunks created: {result['chunks_count']}")
```

---

## ✨ Tính Năng Chính

✅ **Multi-Stage Processing**
- PDF/DOCX → Markdown → Level 1 Chunks → Level 2 Chunks

✅ **Hỗ Trợ Tiếng Việt**
- Tokenization chính xác
- Nhận diện container types (20', 40', 45')
- Extract dates, references, terminology
- Xóa watermark tự động

✅ **Multiple Document Types**
- Pricing (Biểu giá)
- Regulation (Quy định)
- Contract, SOP, Report (có thể thêm)

✅ **Smart Chunking**
- Level 1: 1500-3000 tokens
- Level 2: 500-1500 tokens
- Preserve tables, sections, clauses

✅ **Relationship Mapping**
- Cross-references (Bảng X, Điều Y)
- Parent-child relationships
- Domain relationships (surcharge, exception)

✅ **REST API**
- Upload & process documents
- Search chunks
- Get relationships
- Advanced filtering

---

## 🛠️ Requirements

- Python 3.8+
- FastAPI
- PyMuPDF (PDF processing)
- underthesea/pyvi (Vietnamese NLP)

Tất cả trong `requirements.txt`

---

## ❓ Câu Hỏi Thường Gặp

**Q: Server không start được?**
A: Kiểm tra port 8000 có bị chiếm không. Dùng `uvicorn src.api:app --port 8001`

**Q: Import errors?**
A: Chạy `pip install -r requirements.txt`

**Q: Không tìm thấy schemas?**
A: Kiểm tra `config/schemas/` có file `.yaml` không

**Q: Upload file bị lỗi?**
A: Kiểm tra file format (.pdf, .docx, .md) và document_type đúng

**Q: Làm sao thêm document type mới?**
A: Tạo file YAML mới trong `config/schemas/`

---

## 📞 Trợ Giúp

- 📖 Đọc README.md
- 📋 Xem logs: `logs/app.log`
- 🌐 API Docs: http://localhost:8000/docs
- 🐛 Report issue on GitHub

---

## 🎉 Bắt Đầu Ngay!

```bash
# 1. Cài đặt
pip install -r requirements.txt

# 2. Start server
python run.py

# 3. Mở browser
# http://localhost:8000/docs
```

**Happy Chunking! 🚀**

---

*Được xây dựng với ❤️ bằng FastAPI, PyMuPDF, và underthesea*
