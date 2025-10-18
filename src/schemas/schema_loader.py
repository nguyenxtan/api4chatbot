"""
Schema loader and validator for document types.
"""
import os
from pathlib import Path
from typing import Dict, Optional
import yaml
from loguru import logger

from src.models import DocumentSchema


class SchemaLoader:
    """Loads and manages document type schemas."""

    def __init__(self, schemas_dir: str = "config/schemas"):
        """
        Initialize schema loader.

        Args:
            schemas_dir: Directory containing YAML schema files
        """
        self.schemas_dir = Path(schemas_dir)
        self._schemas_cache: Dict[str, DocumentSchema] = {}
        self._load_all_schemas()

    def _load_all_schemas(self) -> None:
        """Load all schema files from the schemas directory."""
        if not self.schemas_dir.exists():
            logger.warning(f"Schemas directory not found: {self.schemas_dir}")
            return

        for schema_file in self.schemas_dir.glob("*.yaml"):
            try:
                schema = self._load_schema_file(schema_file)
                self._schemas_cache[schema.document_type] = schema
                logger.info(f"Loaded schema: {schema.document_type} from {schema_file.name}")
            except Exception as e:
                logger.error(f"Failed to load schema {schema_file.name}: {e}")

    def _load_schema_file(self, file_path: Path) -> DocumentSchema:
        """
        Load a single schema file.

        Args:
            file_path: Path to YAML schema file

        Returns:
            DocumentSchema instance

        Raises:
            ValueError: If schema is invalid
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            schema_dict = yaml.safe_load(f)

        # Validate and create DocumentSchema
        try:
            schema = DocumentSchema(**schema_dict)
            return schema
        except Exception as e:
            raise ValueError(f"Invalid schema in {file_path.name}: {e}")

    def get_schema(self, document_type: str) -> Optional[DocumentSchema]:
        """
        Get schema for a document type.

        Args:
            document_type: Document type identifier

        Returns:
            DocumentSchema if found, None otherwise
        """
        return self._schemas_cache.get(document_type)

    def get_all_schemas(self) -> Dict[str, DocumentSchema]:
        """Get all loaded schemas."""
        return self._schemas_cache.copy()

    def reload_schema(self, document_type: str) -> Optional[DocumentSchema]:
        """
        Reload a specific schema from disk.

        Args:
            document_type: Document type to reload

        Returns:
            Reloaded DocumentSchema if found
        """
        schema_file = self.schemas_dir / f"{document_type}_schema.yaml"
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return None

        try:
            schema = self._load_schema_file(schema_file)
            self._schemas_cache[document_type] = schema
            logger.info(f"Reloaded schema: {document_type}")
            return schema
        except Exception as e:
            logger.error(f"Failed to reload schema {document_type}: {e}")
            return None

    def validate_schema(self, schema_dict: dict) -> bool:
        """
        Validate a schema dictionary.

        Args:
            schema_dict: Schema dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            DocumentSchema(**schema_dict)
            return True
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    def list_available_schemas(self) -> list[str]:
        """Get list of available document types."""
        return list(self._schemas_cache.keys())


# Global schema loader instance
_schema_loader: Optional[SchemaLoader] = None


def get_schema_loader(schemas_dir: str = "config/schemas") -> SchemaLoader:
    """
    Get or create global schema loader instance.

    Args:
        schemas_dir: Directory containing schema files

    Returns:
        SchemaLoader instance
    """
    global _schema_loader
    if _schema_loader is None:
        _schema_loader = SchemaLoader(schemas_dir)
    return _schema_loader
