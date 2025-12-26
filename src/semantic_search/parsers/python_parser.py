"""
Python parser module.

Uses Python AST (Abstract Syntax Tree) to extract functions, classes,
methods, and imports from Python source files.
"""

import ast
from pathlib import Path
from typing import Optional

from semantic_search.parsers.base_parser import BaseParser, CodeChunk


class PythonParser(BaseParser):
    """
    Parser for Python source files using AST.

    Extracts:
    - Functions with docstrings and signatures
    - Classes with methods
    - Import statements
    """

    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a Python file."""
        return file_path.suffix == '.py'

    def parse(self, file_path: Path, content: str) -> list[CodeChunk]:
        """
        Parse Python file and extract code chunks.

        Args:
            file_path: Path to the Python file
            content: File content as string

        Returns:
            List of CodeChunk objects
        """
        chunks = []

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return chunks

        # Split content into lines for extracting code
        lines = content.splitlines()

        # Extract chunks from AST
        # Use tree.body instead of ast.walk to avoid processing nested nodes multiple times
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                chunk = self._parse_function(node, file_path, lines)
                if chunk:
                    chunks.append(chunk)

            elif isinstance(node, ast.AsyncFunctionDef):
                chunk = self._parse_function(node, file_path, lines, is_async=True)
                if chunk:
                    chunks.append(chunk)

            elif isinstance(node, ast.ClassDef):
                chunk = self._parse_class(node, file_path, lines)
                if chunk:
                    chunks.append(chunk)

                # Also parse methods within the class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_chunk = self._parse_method(
                            item, node.name, file_path, lines,
                            is_async=isinstance(item, ast.AsyncFunctionDef)
                        )
                        if method_chunk:
                            chunks.append(method_chunk)

        return chunks

    def _parse_function(
        self,
        node: ast.FunctionDef,
        file_path: Path,
        lines: list[str],
        is_async: bool = False
    ) -> Optional[CodeChunk]:
        """
        Parse a function definition.

        Args:
            node: AST FunctionDef node
            file_path: Path to the file
            lines: File lines
            is_async: Whether this is an async function

        Returns:
            CodeChunk or None
        """
        # Skip methods (they're handled separately)
        # Check if this function is inside a class
        if self._is_method(node):
            return None

        start_line = node.lineno
        end_line = node.end_lineno if node.end_lineno else start_line

        # Extract signature
        signature = self._build_signature(node, is_async=is_async)

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract code
        code = self._extract_code(lines, start_line - 1, end_line)

        return CodeChunk(
            file_path=str(file_path),
            chunk_type="function",
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            signature=signature,
            docstring=docstring,
            code=code,
            parent=None,
        )

    def _parse_method(
        self,
        node: ast.FunctionDef,
        class_name: str,
        file_path: Path,
        lines: list[str],
        is_async: bool = False
    ) -> Optional[CodeChunk]:
        """
        Parse a class method.

        Args:
            node: AST FunctionDef node
            class_name: Name of the parent class
            file_path: Path to the file
            lines: File lines
            is_async: Whether this is an async method

        Returns:
            CodeChunk or None
        """
        start_line = node.lineno
        end_line = node.end_lineno if node.end_lineno else start_line

        # Extract signature
        signature = self._build_signature(node, is_async=is_async)

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract code
        code = self._extract_code(lines, start_line - 1, end_line)

        return CodeChunk(
            file_path=str(file_path),
            chunk_type="method",
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            signature=signature,
            docstring=docstring,
            code=code,
            parent=class_name,
        )

    def _parse_class(
        self,
        node: ast.ClassDef,
        file_path: Path,
        lines: list[str]
    ) -> Optional[CodeChunk]:
        """
        Parse a class definition.

        Args:
            node: AST ClassDef node
            file_path: Path to the file
            lines: File lines

        Returns:
            CodeChunk or None
        """
        start_line = node.lineno
        end_line = node.end_lineno if node.end_lineno else start_line

        # Extract signature
        signature = self._build_class_signature(node)

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract code (just the class definition, not methods)
        # For classes, we'll include just the header and docstring
        # Methods are parsed separately
        code = self._extract_code(lines, start_line - 1, min(start_line + 10, end_line))

        return CodeChunk(
            file_path=str(file_path),
            chunk_type="class",
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            signature=signature,
            docstring=docstring,
            code=code,
            parent=None,
        )

    def _build_signature(self, node: ast.FunctionDef, is_async: bool = False) -> str:
        """
        Build function signature string.

        Args:
            node: AST FunctionDef node
            is_async: Whether this is an async function

        Returns:
            Signature string
        """
        prefix = "async def" if is_async else "def"

        # Build parameters
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        params = ", ".join(args)

        # Build return type
        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"

        return f"{prefix} {node.name}({params}){returns}:"

    def _build_class_signature(self, node: ast.ClassDef) -> str:
        """
        Build class signature string.

        Args:
            node: AST ClassDef node

        Returns:
            Signature string
        """
        bases = []
        for base in node.bases:
            bases.append(ast.unparse(base))

        bases_str = ""
        if bases:
            bases_str = f"({', '.join(bases)})"

        return f"class {node.name}{bases_str}:"

    def _extract_code(self, lines: list[str], start_idx: int, end_idx: int) -> str:
        """
        Extract code lines from file.

        Args:
            lines: List of file lines
            start_idx: Start index (0-based)
            end_idx: End index (0-based, inclusive)

        Returns:
            Code as string
        """
        if start_idx < 0 or end_idx > len(lines):
            return ""

        return "\n".join(lines[start_idx:end_idx])

    def _is_method(self, node: ast.FunctionDef) -> bool:
        """
        Check if a function is a method (inside a class).

        This is a simple heuristic - in practice, we handle this
        by parsing classes first and their methods separately.

        Args:
            node: AST FunctionDef node

        Returns:
            True if likely a method
        """
        # This is called during ast.walk, which flattens the tree
        # We can't easily determine if it's inside a class here
        # So we'll return False and handle methods in _parse_class
        return False
