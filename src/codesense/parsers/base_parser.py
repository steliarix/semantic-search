"""
Base parser module.

Defines the abstract base class for all parsers and the CodeChunk dataclass
for representing code chunks.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CodeChunk:
    """
    Represents a chunk of code (function, class, method, etc.).

    Attributes:
        chunk_id: Unique identifier for the chunk
        file_path: Path to the source file
        chunk_type: Type of chunk (function, class, method, import, etc.)
        name: Name of the function/class/method
        start_line: Starting line number in the file
        end_line: Ending line number in the file
        signature: Function/class signature
        docstring: Documentation string
        code: The actual code content
        parent: Parent class name (for methods)
        imports: List of imports (for import chunks)
        framework_type: Framework-specific type (django_model, fastapi_route, etc.)
        decorators: List of decorators applied to the function/class
        base_classes: List of base classes (for classes)
        http_method: HTTP method for routes (GET, POST, etc.)
        route_path: URL path for routes
        model_fields: List of model fields (for Django/Pydantic models)
    """
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str = ""
    chunk_type: str = ""  # function, class, method, import, module
    name: str = ""
    start_line: int = 0
    end_line: int = 0
    signature: str = ""
    docstring: Optional[str] = None
    code: str = ""
    parent: Optional[str] = None
    imports: list[str] = field(default_factory=list)
    framework_type: Optional[str] = None  # django_model, django_view, fastapi_route, pydantic_model, etc.
    decorators: list[str] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    http_method: Optional[str] = None  # GET, POST, PUT, DELETE, etc.
    route_path: Optional[str] = None  # URL path for routes
    model_fields: list[str] = field(default_factory=list)  # Model field names

    def to_dict(self) -> dict:
        """Convert CodeChunk to dictionary for storage."""
        return {
            "chunk_id": self.chunk_id,
            "file_path": self.file_path,
            "type": self.chunk_type,
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "docstring": self.docstring,
            "parent": self.parent,
            "imports": self.imports,
            "framework_type": self.framework_type,
            "decorators": self.decorators,
            "base_classes": self.base_classes,
            "http_method": self.http_method,
            "route_path": self.route_path,
            "model_fields": self.model_fields,
        }

    def get_searchable_text(self) -> str:
        """
        Get text representation for creating embeddings.

        Combines signature, docstring, and code for semantic search.
        """
        parts = []

        if self.signature:
            parts.append(self.signature)

        if self.docstring:
            parts.append(self.docstring)

        if self.code:
            parts.append(self.code)

        return "\n\n".join(parts)


class BaseParser(ABC):
    """
    Abstract base class for all code parsers.

    Subclasses must implement the parse() method to extract code chunks
    from source files.
    """

    @abstractmethod
    def parse(self, file_path: Path, content: str) -> list[CodeChunk]:
        """
        Parse a source file and extract code chunks.

        Args:
            file_path: Path to the source file
            content: Content of the file as string

        Returns:
            List of CodeChunk objects
        """
        pass

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this parser can handle the given file.

        Args:
            file_path: Path to the file

        Returns:
            True if this parser can handle the file
        """
        pass
