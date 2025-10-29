"""
Vietnamese text parsing and NLP utilities.
"""
import re
from typing import List, Tuple, Optional, Dict
from loguru import logger

try:
    from underthesea import word_tokenize
    UNDERTHESEA_AVAILABLE = True
except ImportError:
    logger.warning("underthesea not available, using fallback tokenization")
    UNDERTHESEA_AVAILABLE = False

try:
    from pyvi import ViTokenizer
    PYVI_AVAILABLE = True
except ImportError:
    logger.warning("pyvi not available, using fallback tokenization")
    PYVI_AVAILABLE = False


class VietnameseTextParser:
    """Utilities for parsing Vietnamese text."""

    # Common Vietnamese abbreviations in business/legal documents
    ABBREVIATIONS = {
        "TT": "Thông tư",
        "NĐ": "Nghị định",
        "QĐ": "Quyết định",
        "LĐ": "Luật định",
        "CP": "Chính phủ",
        "TTg": "Thủ tướng",
        "GP": "General Purpose",
        "DC": "Dry Container",
        "HC": "High Cube",
        "OT": "Open Top",
        "FR": "Flat Rack",
    }

    # Vietnamese ordinal patterns
    ORDINAL_PATTERNS = [
        r"ngày\s+thứ\s+\d+",           # ngày thứ 1, ngày thứ 2
        r"từ\s+ngày\s+thứ\s+\d+",      # từ ngày thứ 4
        r"tuần\s+thứ\s+\d+",           # tuần thứ 1
        r"tháng\s+thứ\s+\d+",          # tháng thứ 1
    ]

    # Vietnamese conditional markers
    CONDITIONAL_MARKERS = [
        "trong trường hợp",
        "nếu",
        "khi",
        "trừ khi",
        "với điều kiện",
        "ngoài trừ",
        "không áp dụng",
        "riêng đối với",
    ]

    # Vietnamese calculation/pricing terms
    CALCULATION_TERMS = [
        "tính lũy tiến",
        "tính từ",
        "tính bằng",
        "tính theo",
        "không vượt quá",
        "cộng thêm",
        "trừ đi",
        "nhân với",
        "chia cho",
        "phần trăm",
        "%",
    ]

    def __init__(self, tokenizer: str = "underthesea"):
        """
        Initialize Vietnamese parser.

        Args:
            tokenizer: Tokenizer to use ("underthesea" or "pyvi")
        """
        self.tokenizer_type = tokenizer
        self._validate_tokenizer()

    def _validate_tokenizer(self) -> None:
        """Validate tokenizer availability."""
        if self.tokenizer_type == "underthesea" and not UNDERTHESEA_AVAILABLE:
            logger.warning("underthesea requested but not available, falling back to pyvi")
            self.tokenizer_type = "pyvi"

        if self.tokenizer_type == "pyvi" and not PYVI_AVAILABLE:
            logger.warning("pyvi requested but not available, using basic tokenization")
            self.tokenizer_type = "basic"

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize Vietnamese text.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        if not text:
            return []

        if self.tokenizer_type == "underthesea":
            return word_tokenize(text, format="text").split()
        elif self.tokenizer_type == "pyvi":
            return ViTokenizer.tokenize(text).split()
        else:
            # Basic tokenization (fallback)
            return text.split()

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        return len(self.tokenize(text))

    def extract_ordinals(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Extract Vietnamese ordinal expressions.

        Args:
            text: Text to analyze

        Returns:
            List of (ordinal_text, start_pos, end_pos)
        """
        results = []
        for pattern in self.ORDINAL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                results.append((match.group(0), match.start(), match.end()))
        return results

    def extract_conditionals(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Extract conditional expressions.

        Args:
            text: Text to analyze

        Returns:
            List of (conditional_text, start_pos, end_pos)
        """
        results = []
        for marker in self.CONDITIONAL_MARKERS:
            pattern = re.escape(marker)
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract context around the marker
                start = match.start()
                # Find end of sentence
                end = text.find(".", start)
                if end == -1 or end > start + 200:  # Limit context size
                    end = min(start + 200, len(text))
                results.append((text[start:end].strip(), start, end))
        return results

    def extract_calculations(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Extract calculation expressions.

        Args:
            text: Text to analyze

        Returns:
            List of (calculation_text, start_pos, end_pos)
        """
        results = []
        for term in self.CALCULATION_TERMS:
            pattern = re.escape(term)
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.start()
                # Extract context
                end = text.find(".", start)
                if end == -1 or end > start + 150:
                    end = min(start + 150, len(text))
                results.append((text[start:end].strip(), start, end))
        return results

    def extract_container_types(self, text: str) -> List[str]:
        """
        Extract container type references.

        Args:
            text: Text to analyze

        Returns:
            List of container types (e.g., ["20'", "40' HC"])
        """
        pattern = r"(20'|40'|45')(?:\s*(DC|GP|HC|OT|FR))?"
        matches = re.findall(pattern, text)
        return [f"{size} {type_}".strip() if type_ else size for size, type_ in matches]

    def extract_table_references(self, text: str) -> List[Dict[str, str]]:
        """
        Extract table references (e.g., "Bảng 23", "Bảng IV").

        Args:
            text: Text to analyze

        Returns:
            List of dictionaries with table reference info
        """
        # Pattern: Bảng + (number | roman numeral | number-letter)
        pattern = r"Bảng\s+((?:\d+)|(?:[IVX]+)|(?:\d+-[A-Z]+)|(?:\d+-TT\.\d+))"
        matches = re.finditer(pattern, text, re.IGNORECASE)

        results = []
        for match in matches:
            results.append({
                "text": match.group(0),
                "identifier": match.group(1),
                "position": match.start(),
            })
        return results

    def extract_article_references(self, text: str) -> List[Dict[str, str]]:
        """
        Extract article references (e.g., "Điều 15", "Khoản 3 Điều 10").

        Args:
            text: Text to analyze

        Returns:
            List of dictionaries with article reference info
        """
        results = []

        # Pattern: Điều + number
        pattern_article = r"Điều\s+(\d+)"
        for match in re.finditer(pattern_article, text):
            results.append({
                "type": "article",
                "text": match.group(0),
                "article_number": match.group(1),
                "position": match.start(),
            })

        # Pattern: Khoản + number + Điều + number
        pattern_clause = r"Khoản\s+(\d+)\s+Điều\s+(\d+)"
        for match in re.finditer(pattern_clause, text):
            results.append({
                "type": "clause",
                "text": match.group(0),
                "clause_number": match.group(1),
                "article_number": match.group(2),
                "position": match.start(),
            })

        # Pattern: Điểm + letter + Khoản + number + Điều + number
        pattern_point = r"Điểm\s+([a-z])\s+Khoản\s+(\d+)\s+Điều\s+(\d+)"
        for match in re.finditer(pattern_point, text):
            results.append({
                "type": "point",
                "text": match.group(0),
                "point_letter": match.group(1),
                "clause_number": match.group(2),
                "article_number": match.group(3),
                "position": match.start(),
            })

        return results

    def extract_legal_document_references(self, text: str) -> List[Dict[str, str]]:
        """
        Extract legal document references.

        Args:
            text: Text to analyze

        Returns:
            List of legal document references
        """
        # Pattern: (Luật|Nghị định|Thông tư|Quyết định) + số + number/year
        pattern = r"(Luật|Nghị định|Thông tư|Quyết định)\s+(?:số\s+)?(\d+[/-]\d+(?:[/-][A-Z]+)?)"
        matches = re.finditer(pattern, text, re.IGNORECASE)

        results = []
        for match in matches:
            results.append({
                "type": match.group(1),
                "identifier": match.group(2),
                "text": match.group(0),
                "position": match.start(),
            })
        return results

    def extract_dates(self, text: str) -> List[Dict[str, str]]:
        """
        Extract Vietnamese date expressions.

        Args:
            text: Text to analyze

        Returns:
            List of date dictionaries
        """
        results = []

        # Pattern: DD/MM/YYYY or DD-MM-YYYY
        pattern_numeric = r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
        for match in re.finditer(pattern_numeric, text):
            results.append({
                "format": "numeric",
                "text": match.group(0),
                "position": match.start(),
            })

        # Pattern: ngày DD tháng MM năm YYYY
        pattern_verbal = r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})"
        for match in re.finditer(pattern_verbal, text, re.IGNORECASE):
            day, month, year = match.groups()
            results.append({
                "format": "verbal",
                "text": match.group(0),
                "day": day,
                "month": month,
                "year": year,
                "position": match.start(),
            })

        return results

    def normalize_abbreviations(self, text: str) -> str:
        """
        Expand abbreviations in text.

        Args:
            text: Text with abbreviations

        Returns:
            Text with expanded abbreviations
        """
        normalized = text
        for abbr, expansion in self.ABBREVIATIONS.items():
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(abbr) + r"\b"
            normalized = re.sub(pattern, expansion, normalized)
        return normalized

    def split_sentences(self, text: str) -> List[str]:
        """
        Split Vietnamese text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Vietnamese sentence endings
        sentence_endings = r"[.!?;]\s+"
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]

    def is_heading(self, text: str) -> bool:
        """
        Check if text is likely a heading.

        Args:
            text: Text to check

        Returns:
            True if likely a heading
        """
        # Check for heading markers
        heading_patterns = [
            r"^#{1,6}\s+",          # Markdown headings
            r"^[IVX]+\.\s+",        # Roman numerals
            r"^\d+\.\s+",           # Arabic numerals
            r"^Chương\s+[IVX\d]+",  # Chapter
            r"^Mục\s+\d+",          # Section
            r"^Điều\s+\d+",         # Article
        ]

        for pattern in heading_patterns:
            if re.match(pattern, text.strip()):
                return True

        # Check if short and mostly capitalized (heuristic)
        if len(text) < 100 and text.isupper():
            return True

        return False

    def extract_pricing_info(self, text: str) -> Dict[str, any]:
        """
        Extract pricing information from text.

        Args:
            text: Text containing pricing info

        Returns:
            Dictionary with extracted pricing data
        """
        info = {
            "amounts": [],
            "currencies": [],
            "units": [],
            "conditions": [],
        }

        # Extract amounts (VND, USD, EUR)
        amount_pattern = r"([\d,\.]+)\s*(VND|USD|EUR)"
        for match in re.finditer(amount_pattern, text):
            info["amounts"].append({
                "value": match.group(1),
                "currency": match.group(2),
            })

        # Extract units
        unit_pattern = r"/(container|tấn|cbm|chuyến|lượt|ngày)"
        for match in re.finditer(unit_pattern, text, re.IGNORECASE):
            info["units"].append(match.group(1))

        # Extract conditions
        for marker in self.CONDITIONAL_MARKERS:
            if marker in text.lower():
                info["conditions"].append(marker)

        return info
