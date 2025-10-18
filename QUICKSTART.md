# Quick Start Guide

Get started with the Multi-Document Chunking Pipeline API in 5 minutes.

## 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd api4chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data/chunks logs temp examples
```

## 2. Start the Server

```bash
# Option 1: Using run.py
python run.py

# Option 2: Using uvicorn directly
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## 3. Upload Your First Document

### Using cURL

```bash
curl -X POST "http://localhost:8000/documents/process" \
  -F "file=@your_document.pdf" \
  -F "document_type=pricing" \
  -F "document_name=My Document" \
  -F "tags=test,demo"
```

### Using Python

```python
import requests

# Upload document
with open("your_document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/documents/process",
        files={"file": f},
        data={
            "document_type": "pricing",
            "document_name": "My Document",
            "tags": "test,demo"
        }
    )

result = response.json()
print(f"Document ID: {result['document_id']}")
print(f"Chunks created: {result['chunks_count']}")
```

### Using the API Docs UI

1. Go to `http://localhost:8000/docs`
2. Click on `POST /documents/process`
3. Click "Try it out"
4. Upload your file and fill in parameters
5. Click "Execute"

## 4. Query Your Chunks

### Get All Chunks
```bash
curl "http://localhost:8000/documents/{document_id}/chunks"
```

### Get Level 1 Chunks Only
```bash
curl "http://localhost:8000/documents/{document_id}/chunks?level=1"
```

### Get Specific Chunk
```bash
curl "http://localhost:8000/chunks/{chunk_id}"
```

### Get Related Chunks
```bash
curl "http://localhost:8000/chunks/{chunk_id}/relationships"
```

## 5. Search with Filters

```python
import requests

# Search for table chunks with specific container types
query = {
    "chunk_type": "table",
    "metadata_filter": {
        "container_types": ["20'", "40'"]
    },
    "limit": 10
}

response = requests.post(
    "http://localhost:8000/chunks/search",
    json=query
)

chunks = response.json()
for chunk in chunks:
    print(f"{chunk['chunk_id']}: {chunk['title']}")
```

## Supported Document Types

Current schemas available:
- `pricing` - Pricing documents (Biểu giá dịch vụ)
- `regulation` - Regulatory documents (Quy định, hướng dẫn)

More schemas can be added in `config/schemas/`

## Supported File Formats

- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- Markdown (`.md`)
- Plain Text (`.txt`)

## Example Workflow

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Process document
with open("pricing_doc.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/documents/process",
        files={"file": f},
        data={"document_type": "pricing"}
    )
doc_id = response.json()["document_id"]

# 2. Get all level 1 chunks
chunks = requests.get(f"{BASE_URL}/documents/{doc_id}/chunks?level=1").json()

# 3. Get details of first chunk
chunk_id = chunks[0]["chunk_id"]
chunk = requests.get(f"{BASE_URL}/chunks/{chunk_id}").json()

print(f"Title: {chunk['title']}")
print(f"Type: {chunk['type']}")
print(f"Content: {chunk['content'][:200]}...")

# 4. Get related chunks (e.g., surcharges)
related = requests.get(
    f"{BASE_URL}/chunks/{chunk_id}/relationships?relationship_type=surcharge"
).json()

print(f"Found {len(related)} surcharge-related chunks")
```

## Troubleshooting

### API won't start
- Check if port 8000 is already in use
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check logs in `logs/` directory

### Document processing fails
- Verify file format is supported
- Check file is not corrupted
- Ensure `document_type` matches an available schema
- Check logs for detailed error messages

### No chunks created
- Document might be empty or unreadable
- Schema might not match document structure
- Check warnings in the processing result

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore API documentation at `http://localhost:8000/docs`
- Check example scripts in `examples/`
- Customize schemas in `config/schemas/`
- Integrate with your RAG/embedding pipeline

## Need Help?

- Check API docs: `http://localhost:8000/docs`
- View logs: `logs/app.log` and `logs/errors.log`
- Open an issue on GitHub

## Quick Reference

### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/documents/process` | POST | Upload and process document |
| `/documents` | GET | List all documents |
| `/documents/{id}/chunks` | GET | Get chunks for document |
| `/chunks/{id}` | GET | Get specific chunk |
| `/chunks/{id}/relationships` | GET | Get related chunks |
| `/chunks/search` | POST | Search with filters |
| `/schemas` | GET | List available schemas |

### Document Types

- `pricing` - Pricing/tariff documents
- `regulation` - Regulatory/policy documents
- `contract` - Legal contracts (add schema)
- `sop` - Standard operating procedures (add schema)
- `report` - Financial/analytical reports (add schema)

### Chunk Types

**Level 1:**
- `section` - Document section
- `table` - Full table
- `article` - Regulatory article
- `chapter` - Document chapter

**Level 2:**
- `row_group` - Table row grouping
- `clause` - Specific clause
- `definition` - Term definition
- `condition` - Conditional rule
- `rule` - Extracted rule

### Relationship Types

- `parent` - Parent chunk
- `child` - Child chunk
- `reference` - Cross-reference
- `surcharge` - Surcharge rule
- `exception` - Exception rule
- `prerequisite` - Prerequisite condition
