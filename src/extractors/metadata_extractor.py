"""
Metadata extraction from documents based on schemas.
"""
import re
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from loguru import logger

from src.models import DocumentSchema
from src.extractors.vietnamese_parser import VietnameseTextParser


class MetadataExtractor:
    """Extract metadata from document chunks based on schema rules."""

    def __init__(self, parser: Optional[VietnameseTextParser] = None):
        """
        Initialize metadata extractor.

        Args:
            parser: Vietnamese text parser (creates new one if None)
        """
        self.parser = parser or VietnameseTextParser()

    def extract_metadata(
        self,
        text: str,
        schema: DocumentSchema,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract metadata fields from text according to schema.

        Args:
            text: Text to extract from
            schema: Document schema with extraction rules
            context: Optional surrounding context

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}

        # Combine text and context for extraction
        full_text = f"{context}\n{text}" if context else text

        # Extract each metadata field defined in schema
        for field in schema.first_level_metadata_fields:
            if field in schema.metadata_extractors:
                extractor_config = schema.metadata_extractors[field]
                value = self._extract_field(field, full_text, extractor_config)
                if value is not None:
                    metadata[field] = value
            else:
                # Use default extraction for common fields
                value = self._extract_common_field(field, full_text)
                if value is not None:
                    metadata[field] = value

        return metadata

    def _extract_field(
        self,
        field_name: str,
        text: str,
        config: Dict[str, Any]
    ) -> Any:
        """
        Extract a specific field using configuration.

        Args:
            field_name: Name of field
            text: Text to extract from
            config: Extraction configuration

        Returns:
            Extracted value or None
        """
        # Pattern-based extraction
        if "patterns" in config:
            patterns = config["patterns"]
            if isinstance(patterns, str):
                patterns = [patterns]

            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if config.get("extract_all", False):
                        return matches
                    else:
                        return matches[0] if isinstance(matches[0], str) else matches[0][0]

        # Keyword/vocabulary-based extraction
        if "keywords" in config or "vocabulary" in config:
            keywords = config.get("keywords", config.get("vocabulary", []))
            found = []
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    found.append(keyword)

            if found:
                return found if config.get("extract_all", False) else found[0]

        return None

    def _extract_common_field(self, field_name: str, text: str) -> Any:
        """Extract common metadata fields with default patterns."""

        # Heading path
        if field_name == "heading_path":
            return self._extract_heading_path(text)

        # Page range
        elif field_name == "page_range":
            return self._extract_page_range(text)

        # Effective date
        elif field_name == "effective_date":
            return self._extract_effective_date(text)

        # Container types
        elif field_name == "container_types":
            return self.parser.extract_container_types(text)

        # Service type
        elif field_name == "service_type":
            return self._extract_service_type(text)

        # Unit
        elif field_name == "unit":
            return self._extract_unit(text)

        # Applies to
        elif field_name == "applies_to":
            return self._extract_applies_to(text)

        # References
        elif field_name == "references":
            return self._extract_references(text)

        # Article number
        elif field_name == "article_number":
            return self._extract_article_number(text)

        # Chapter number
        elif field_name == "chapter_number":
            return self._extract_chapter_number(text)

        # Section number
        elif field_name == "section_number":
            return self._extract_section_number(text)

        return None

    def _extract_heading_path(self, text: str) -> Optional[str]:
        """Extract heading hierarchy path."""
        # Look for markdown headings
        lines = text.split("\n")
        headings = []

        for line in lines[:20]:  # Check first 20 lines
            match = re.match(r"^(#{1,6})\s+(.+)", line)
            if match:
                level = len(match.group(1))
                heading_text = match.group(2).strip()
                headings.append((level, heading_text))

        if not headings:
            return None

        # Build path from headings
        # Keep only progressively deeper levels
        path = []
        last_level = 0
        for level, text in headings:
            if level > last_level:
                path.append(text)
                last_level = level
            elif level <= last_level and path:
                # Replace at same level
                path[-1] = text

        return " > ".join(path) if path else None

    def _extract_page_range(self, text: str) -> Optional[str]:
        """Extract page range references."""
        # Pattern: "Trang 4-6", "p. 10-15", etc.
        patterns = [
            r"(?:Trang|trang|p\.|page)\s*(\d+)\s*[-–]\s*(\d+)",
            r"(?:Trang|trang|p\.|page)\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    return f"{match.group(1)}-{match.group(2)}"
                else:
                    return match.group(1)

        return None

    def _extract_effective_date(self, text: str) -> Optional[date]:
        """Extract effective date."""
        dates = self.parser.extract_dates(text)

        # Look for dates near "hiệu lực" or "áp dụng"
        for date_info in dates:
            context_start = max(0, date_info["position"] - 50)
            context_end = min(len(text), date_info["position"] + 50)
            context = text[context_start:context_end].lower()

            if "hiệu lực" in context or "áp dụng" in context:
                # Parse date
                date_str = date_info["text"]
                return self._parse_date(date_str)

        # If no context match, return first date found
        if dates:
            return self._parse_date(dates[0]["text"])

        return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse Vietnamese date string to date object."""
        # Try different formats
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d/%m/%y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _extract_service_type(self, text: str) -> Optional[str]:
        """Extract service type."""
        service_types = [
            "Xếp dỡ",
            "Lưu bãi",
            "Nâng hạ",
            "Vận chuyển",
            "Niêm phong",
            "Đóng mở cửa",
            "Làm hàng",
            "Cân container",
            "Kiểm định",
        ]

        for service in service_types:
            if service.lower() in text.lower():
                return service

        return None

    def _extract_unit(self, text: str) -> Optional[str]:
        """Extract pricing/measurement unit."""
        unit_patterns = [
            r"(VND|USD|EUR)/(container|tấn|cbm|chuyến|lượt|ngày|giờ)",
            r"đồng/(container|tấn|cbm)",
        ]

        for pattern in unit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    def _extract_applies_to(self, text: str) -> List[str]:
        """Extract applicability scope."""
        applies_to = []

        # Container types
        if "container hàng" in text.lower() or "cont hàng" in text.lower():
            applies_to.append("container_hàng")
        if "container rỗng" in text.lower() or "cont rỗng" in text.lower():
            applies_to.append("container_rỗng")

        # Cargo types
        if "hàng nguy hiểm" in text.lower():
            applies_to.append("hàng_nguy_hiểm")
        if "hàng quá khổ" in text.lower():
            applies_to.append("hàng_quá_khổ")

        # Customer types
        if "khách hàng VIP" in text.lower():
            applies_to.append("khách_hàng_VIP")

        return applies_to

    def _extract_references(self, text: str) -> List[str]:
        """Extract all references to other sections/tables."""
        references = []

        # Table references
        table_refs = self.parser.extract_table_references(text)
        for ref in table_refs:
            references.append(ref["text"])

        # Article references
        article_refs = self.parser.extract_article_references(text)
        for ref in article_refs:
            references.append(ref["text"])

        # Legal document references
        legal_refs = self.parser.extract_legal_document_references(text)
        for ref in legal_refs:
            references.append(ref["text"])

        return list(set(references))  # Remove duplicates

    def _extract_article_number(self, text: str) -> Optional[str]:
        """Extract article number from regulatory text."""
        pattern = r"Điều\s+(\d+)"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None

    def _extract_chapter_number(self, text: str) -> Optional[str]:
        """Extract chapter number."""
        pattern = r"Chương\s+([IVX]+|\d+)"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None

    def _extract_section_number(self, text: str) -> Optional[str]:
        """Extract section number."""
        pattern = r"Mục\s+(\d+)"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None

    def extract_conditions(self, text: str) -> List[Dict[str, str]]:
        """
        Extract conditional clauses from text.

        Returns:
            List of conditions with type and text
        """
        conditions = []
        conditionals = self.parser.extract_conditionals(text)

        for cond_text, start, end in conditionals:
            # Classify condition type
            cond_type = "general"
            if "nếu" in cond_text.lower() or "khi" in cond_text.lower():
                cond_type = "conditional"
            elif "ngoài trừ" in cond_text.lower() or "không áp dụng" in cond_text.lower():
                cond_type = "exception"
            elif "với điều kiện" in cond_text.lower():
                cond_type = "prerequisite"

            conditions.append({
                "type": cond_type,
                "text": cond_text,
                "position": start,
            })

        return conditions

    def extract_pricing_conditions(self, text: str) -> Dict[str, Any]:
        """
        Extract pricing-specific conditions.

        Returns:
            Dictionary with timing, surcharges, discounts, etc.
        """
        conditions = {
            "timing": [],
            "surcharges": [],
            "discounts": [],
            "thresholds": [],
        }

        # Timing conditions (ngày thứ, from-to dates)
        ordinals = self.parser.extract_ordinals(text)
        for ordinal_text, _, _ in ordinals:
            conditions["timing"].append(ordinal_text)

        # Surcharges
        surcharge_pattern = r"phụ thu[^.]{0,100}"
        for match in re.finditer(surcharge_pattern, text, re.IGNORECASE):
            conditions["surcharges"].append(match.group(0))

        # Discounts
        discount_pattern = r"(?:giảm|chiết khấu)[^.]{0,100}"
        for match in re.finditer(discount_pattern, text, re.IGNORECASE):
            conditions["discounts"].append(match.group(0))

        # Thresholds (không vượt quá, tối thiểu, tối đa)
        threshold_pattern = r"(?:không vượt quá|tối thiểu|tối đa|từ|đến)\s+[\d,\.]+"
        for match in re.finditer(threshold_pattern, text, re.IGNORECASE):
            conditions["thresholds"].append(match.group(0))

        return conditions
