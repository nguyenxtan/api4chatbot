# Development & Code Review Notes

**Purpose**: Keep track of code reviews, technical decisions, and implementation notes for future reference when working on api4chatbot project.

---

## Current Approaches & Patterns

### 1. Vietnamese Document Formatting (markdown_to_bullet.py)
**Last Updated**: 2025-10-29
**Status**: ✅ Implemented & Tested

**Pattern**: Multi-level heading hierarchy with box drawing characters
```
# Document Title          → Full underline
## Section               → Section with underline
### Subsection          → Plain text
#### Sub-items          → Bullets with indent
```

**Table Format**: "Phương án" structure with Vietnamese styling
```
┃ PHƯƠNG ÁN 1: Description
┣━━━━━━━━━━━━━━━━━━━━━━━━━
┃ • Item → Value
```

**PDF Artifact Handling**:
- Remove watermark patterns (Vietnamese characters)
- Clean cell content from PDF extraction garbage
- Handle PDF-embedded text (single chars with newlines)

**Files Involved**:
- `src/core/markdown_to_bullet.py` - Main converter
- `src/core/file_cleaner.py` - Watermark removal
- `sample/bang_02_bullets.txt` - Expected output format

---

## Project Structure Decisions

### Documentation Files (Kept)
- **README.md** - Comprehensive main documentation
- **START_HERE.md** - Entry point for users (Vietnamese/English)
- Stored in: `/Users/tannx/Documents/chatbot/api4chatbot/`

### Documentation Files (Removed)
- ~~QUICKSTART.md~~ - Removed (duplicate of README)
- ~~CLEAN_VERSION.md~~ - Removed (outdated cleanup notes)

### Docker Configuration
- **Dockerfile** - Python 3.11-slim, port 8005
- **docker-compose.yml** - Single API service with volumes
- Both files verified from remote: commit `f78da8f`

### Python Source Code
- 22 Python modules in `src/`
- Core modules: API, file cleaner, markdown converter, document splitter
- Extractors: Vietnamese parser, table extractor, metadata
- Storage, schemas, utilities included

---

## Technical Notes for Future Work

### Markdown Converter
1. **Heading Levels**: H1-H4+ have different formatting
2. **Table Structure**: Detect "TT" column for numbering
3. **Arrow Conversion**: Vietnamese directional patterns (Xe ↔ Bãi)
4. **Notes/Remarks**: Detect with "Ghi chú", "Chú ý", "Lưu ý" keywords

### File Cleaning
1. Remove watermark text patterns
2. Handle header/footer with thresholds
3. Preserve legitimate content boundaries
4. Clean PDF extraction artifacts

### API Endpoints
Main endpoints (from `src/api.py`):
- `/documents/cleanfile` - Remove watermarks
- `/documents/markdown` - Convert to markdown
- `/documents/split` - Split by tables
- `/documents/bullet` - Convert to bullet format

---

## Repository State

**Last Cleanup**: 2025-10-29
- Removed temp/ directory (17MB)
- Removed empty git submodules
- Preserved all source code and essential files

**Git History**:
- Main development on `main` branch
- Code reviews and improvements tracked in commits
- Clean branch merging strategy

---

## When to Use This File

✓ Before modifying markdown_to_bullet.py
✓ When adding new document types
✓ If extending PDF cleaning logic
✓ When reviewing API endpoint behavior
✓ For understanding Vietnamese text patterns

---

## Quick Reference

**Start Development**:
```bash
cd /Users/tannx/Documents/chatbot/api4chatbot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

**Run Tests**:
```bash
python test_markdown_bullet.py
python test_api_clean.py
```

**Check Code**:
- API: `src/api.py`
- Markdown: `src/core/markdown_to_bullet.py`
- File Cleaning: `src/core/file_cleaner.py`

---

**Format**: Keep this file focused on technical decisions and patterns
**Location**: `/Users/tannx/Documents/chatbot/.claude/DEVELOPMENT.md`
**Review**: Before major code changes or feature additions
