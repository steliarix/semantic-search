"""
Python parsers module - unified parser collection.

Contains all Python-specific parsers:
- PythonParser: Base Python AST parser
- DjangoParser: Django-specific patterns (models, views, serializers)
- FastAPIParser: FastAPI routes and Pydantic models
- UniversalParser: Auto-detecting multi-framework parser
"""

import ast
import re
from pathlib import Path
from typing import Optional

from codesense.parsers.base_parser import BaseParser, CodeChunk


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

        lines = content.splitlines()

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
        """Parse a function definition."""
        if self._is_method(node):
            return None

        start_line = node.lineno
        end_line = node.end_lineno if node.end_lineno else start_line
        signature = self._build_signature(node, is_async=is_async)
        docstring = ast.get_docstring(node)
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
        """Parse a class method."""
        start_line = node.lineno
        end_line = node.end_lineno if node.end_lineno else start_line
        signature = self._build_signature(node, is_async=is_async)
        docstring = ast.get_docstring(node)
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
        """Parse a class definition."""
        start_line = node.lineno
        end_line = node.end_lineno if node.end_lineno else start_line
        signature = self._build_class_signature(node)
        docstring = ast.get_docstring(node)
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
        """Build function signature string."""
        prefix = "async def" if is_async else "def"
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        params = ", ".join(args)
        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"

        return f"{prefix} {node.name}({params}){returns}:"

    def _build_class_signature(self, node: ast.ClassDef) -> str:
        """Build class signature string."""
        bases = [ast.unparse(base) for base in node.bases]
        bases_str = f"({', '.join(bases)})" if bases else ""
        return f"class {node.name}{bases_str}:"

    def _extract_code(self, lines: list[str], start_idx: int, end_idx: int) -> str:
        """Extract code lines from file."""
        if start_idx < 0 or end_idx > len(lines):
            return ""
        return "\n".join(lines[start_idx:end_idx])

    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if a function is a method."""
        return False


class DjangoParser(PythonParser):
    """
    Parser for Django projects.

    Recognizes Django-specific patterns:
    - Models (models.Model)
    - Views (ViewSets, APIViews, generic views)
    - Serializers (serializers.Serializer, ModelSerializer)
    """

    def parse(self, file_path: Path, content: str) -> list[CodeChunk]:
        """Parse Django file and extract code chunks with Django-specific metadata."""
        chunks = super().parse(file_path, content)

        try:
            tree = ast.parse(content)
            self._enhance_with_django_metadata(chunks, tree, content.splitlines())
        except SyntaxError:
            pass

        return chunks

    def _enhance_with_django_metadata(
        self,
        chunks: list[CodeChunk],
        tree: ast.Module,
        lines: list[str]
    ) -> None:
        """Add Django-specific metadata to chunks."""
        chunk_map = {chunk.name: chunk for chunk in chunks}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                chunk = chunk_map.get(node.name)
                if not chunk:
                    continue

                base_classes = [ast.unparse(base) for base in node.bases]
                chunk.base_classes = base_classes
                chunk.decorators = [ast.unparse(dec) for dec in node.decorator_list]

                if self._is_django_model(base_classes):
                    chunk.framework_type = "django_model"
                    chunk.model_fields = self._extract_model_fields(node)
                elif self._is_django_view(base_classes):
                    chunk.framework_type = "django_view"
                elif self._is_django_serializer(base_classes):
                    chunk.framework_type = "django_serializer"
                    chunk.model_fields = self._extract_model_fields(node)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk = chunk_map.get(node.name)
                if not chunk:
                    continue

                chunk.decorators = [ast.unparse(dec) for dec in node.decorator_list]

                if self._is_view_function(chunk.decorators):
                    chunk.framework_type = "django_view"

    def _is_django_model(self, base_classes: list[str]) -> bool:
        """Check if class is a Django model."""
        django_model_bases = [
            "models.Model", "Model", "AbstractUser", "AbstractBaseUser",
        ]
        return any(base in base_classes for base in django_model_bases)

    def _is_django_view(self, base_classes: list[str]) -> bool:
        """Check if class is a Django view."""
        django_view_bases = [
            "APIView", "ViewSet", "ModelViewSet", "ReadOnlyModelViewSet",
            "GenericViewSet", "View", "ListView", "DetailView", "CreateView",
            "UpdateView", "DeleteView", "TemplateView",
        ]
        return any(
            any(base_pattern in base for base_pattern in django_view_bases)
            for base in base_classes
        )

    def _is_django_serializer(self, base_classes: list[str]) -> bool:
        """Check if class is a Django REST Framework serializer."""
        serializer_bases = [
            "serializers.Serializer", "serializers.ModelSerializer",
            "Serializer", "ModelSerializer", "HyperlinkedModelSerializer",
        ]
        return any(base in base_classes for base in serializer_bases)

    def _is_view_function(self, decorators: list[str]) -> bool:
        """Check if function is a Django view based on decorators."""
        view_decorators = [
            "api_view", "login_required", "permission_required",
            "require_http_methods", "require_GET", "require_POST",
        ]
        return any(
            any(dec_pattern in dec for dec_pattern in view_decorators)
            for dec in decorators
        )

    def _extract_model_fields(self, node: ast.ClassDef) -> list[str]:
        """Extract field names from a Django model or serializer."""
        fields = []

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.append(item.target.id)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if not target.id.startswith('_') and target.id not in ['objects', 'Meta']:
                            fields.append(target.id)

        return fields


class FastAPIParser(PythonParser):
    """
    Parser for FastAPI projects.

    Recognizes FastAPI-specific patterns:
    - Route decorators (@app.get, @app.post, @router.get, etc.)
    - Pydantic models (BaseModel)
    """

    def parse(self, file_path: Path, content: str) -> list[CodeChunk]:
        """Parse FastAPI file and extract code chunks with FastAPI-specific metadata."""
        chunks = super().parse(file_path, content)

        try:
            tree = ast.parse(content)
            self._enhance_with_fastapi_metadata(chunks, tree, content.splitlines())
        except SyntaxError:
            pass

        return chunks

    def _enhance_with_fastapi_metadata(
        self,
        chunks: list[CodeChunk],
        tree: ast.Module,
        lines: list[str]
    ) -> None:
        """Add FastAPI-specific metadata to chunks."""
        chunk_map = {chunk.name: chunk for chunk in chunks}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                chunk = chunk_map.get(node.name)
                if not chunk:
                    continue

                base_classes = [ast.unparse(base) for base in node.bases]
                chunk.base_classes = base_classes
                chunk.decorators = [ast.unparse(dec) for dec in node.decorator_list]

                if self._is_pydantic_model(base_classes):
                    chunk.framework_type = "pydantic_model"
                    chunk.model_fields = self._extract_pydantic_fields(node)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk = chunk_map.get(node.name)
                if not chunk:
                    continue

                chunk.decorators = [ast.unparse(dec) for dec in node.decorator_list]

                route_info = self._extract_route_info(chunk.decorators)
                if route_info:
                    chunk.framework_type = "fastapi_route"
                    chunk.http_method = route_info["method"]
                    chunk.route_path = route_info["path"]

    def _is_pydantic_model(self, base_classes: list[str]) -> bool:
        """Check if class is a Pydantic model."""
        pydantic_bases = ["BaseModel", "pydantic.BaseModel"]
        return any(base in base_classes for base in pydantic_bases)

    def _extract_route_info(self, decorators: list[str]) -> Optional[dict]:
        """Extract route information from decorators."""
        route_patterns = [
            (r'(?:app|router)\.get\(["\']([^"\']+)', "GET"),
            (r'(?:app|router)\.post\(["\']([^"\']+)', "POST"),
            (r'(?:app|router)\.put\(["\']([^"\']+)', "PUT"),
            (r'(?:app|router)\.delete\(["\']([^"\']+)', "DELETE"),
            (r'(?:app|router)\.patch\(["\']([^"\']+)', "PATCH"),
            (r'(?:app|router)\.options\(["\']([^"\']+)', "OPTIONS"),
            (r'(?:app|router)\.head\(["\']([^"\']+)', "HEAD"),
        ]

        for decorator in decorators:
            for pattern, method in route_patterns:
                match = re.search(pattern, decorator)
                if match:
                    return {"method": method, "path": match.group(1)}

        return None

    def _extract_pydantic_fields(self, node: ast.ClassDef) -> list[str]:
        """Extract field names from a Pydantic model."""
        fields = []

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                if not field_name.startswith('_') and field_name != 'Config':
                    fields.append(field_name)

        return fields


class UniversalParser(PythonParser):
    """
    Universal parser that automatically detects and handles multiple frameworks.

    Detects and parses:
    - Django (models, views, serializers, admin)
    - FastAPI (routes, Pydantic models)
    - Flask (routes, blueprints)
    - Generic Python code
    """

    def parse(self, file_path: Path, content: str) -> list[CodeChunk]:
        """Parse file and extract code chunks with framework-specific metadata."""
        chunks = super().parse(file_path, content)

        try:
            tree = ast.parse(content)
            self._enhance_with_framework_metadata(chunks, tree, content.splitlines())
        except SyntaxError:
            pass

        return chunks

    def _enhance_with_framework_metadata(
        self,
        chunks: list[CodeChunk],
        tree: ast.Module,
        lines: list[str]
    ) -> None:
        """Add framework-specific metadata to chunks."""
        chunk_map = {chunk.name: chunk for chunk in chunks}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                chunk = chunk_map.get(node.name)
                if not chunk:
                    continue

                base_classes = [ast.unparse(base) for base in node.bases]
                chunk.base_classes = base_classes
                chunk.decorators = [ast.unparse(dec) for dec in node.decorator_list]

                framework_type = self._detect_class_framework_type(base_classes)
                if framework_type:
                    chunk.framework_type = framework_type

                    if "model" in framework_type:
                        chunk.model_fields = self._extract_model_fields(node)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk = chunk_map.get(node.name)
                if not chunk:
                    continue

                chunk.decorators = [ast.unparse(dec) for dec in node.decorator_list]

                framework_info = self._detect_function_framework_type(chunk.decorators)
                if framework_info:
                    chunk.framework_type = framework_info["type"]
                    chunk.http_method = framework_info.get("method")
                    chunk.route_path = framework_info.get("path")

    def _detect_class_framework_type(self, base_classes: list[str]) -> Optional[str]:
        """Detect framework type from class base classes."""
        django_model_bases = [
            "models.Model", "Model", "AbstractUser", "AbstractBaseUser",
        ]
        if any(base in base_classes for base in django_model_bases):
            return "django_model"

        django_view_bases = [
            "APIView", "ViewSet", "ModelViewSet", "ReadOnlyModelViewSet",
            "GenericViewSet", "View", "ListView", "DetailView", "CreateView",
            "UpdateView", "DeleteView", "TemplateView",
        ]
        if any(any(base_pattern in base for base_pattern in django_view_bases) for base in base_classes):
            return "django_view"

        serializer_bases = [
            "serializers.Serializer", "serializers.ModelSerializer",
            "Serializer", "ModelSerializer", "HyperlinkedModelSerializer",
        ]
        if any(base in base_classes for base in serializer_bases):
            return "django_serializer"

        pydantic_bases = ["BaseModel", "pydantic.BaseModel"]
        if any(base in base_classes for base in pydantic_bases):
            return "pydantic_model"

        if "Blueprint" in base_classes:
            return "flask_blueprint"

        return None

    def _detect_function_framework_type(self, decorators: list[str]) -> Optional[dict]:
        """Detect framework type and route info from function decorators."""
        fastapi_route = self._extract_fastapi_route(decorators)
        if fastapi_route:
            return {
                "type": "fastapi_route",
                "method": fastapi_route["method"],
                "path": fastapi_route["path"]
            }

        flask_route = self._extract_flask_route(decorators)
        if flask_route:
            return {
                "type": "flask_route",
                "method": flask_route["method"],
                "path": flask_route["path"]
            }

        django_view_decorators = [
            "api_view", "login_required", "permission_required",
            "require_http_methods", "require_GET", "require_POST",
        ]
        if any(any(dec_pattern in dec for dec_pattern in django_view_decorators) for dec in decorators):
            method = self._extract_django_http_method(decorators)
            return {
                "type": "django_view",
                "method": method,
                "path": None
            }

        return None

    def _extract_fastapi_route(self, decorators: list[str]) -> Optional[dict]:
        """Extract FastAPI route information from decorators."""
        route_patterns = [
            (r'(?:app|router)\.get\(["\']([^"\']+)', "GET"),
            (r'(?:app|router)\.post\(["\']([^"\']+)', "POST"),
            (r'(?:app|router)\.put\(["\']([^"\']+)', "PUT"),
            (r'(?:app|router)\.delete\(["\']([^"\']+)', "DELETE"),
            (r'(?:app|router)\.patch\(["\']([^"\']+)', "PATCH"),
            (r'(?:app|router)\.options\(["\']([^"\']+)', "OPTIONS"),
            (r'(?:app|router)\.head\(["\']([^"\']+)', "HEAD"),
        ]

        for decorator in decorators:
            for pattern, method in route_patterns:
                match = re.search(pattern, decorator)
                if match:
                    return {"method": method, "path": match.group(1)}

        return None

    def _extract_flask_route(self, decorators: list[str]) -> Optional[dict]:
        """Extract Flask route information from decorators."""
        for decorator in decorators:
            route_match = re.search(r'(?:app|blueprint|\w+)\.route\(["\']([^"\']+)', decorator)
            if route_match:
                path = route_match.group(1)

                methods_match = re.search(r'methods\s*=\s*\[([^\]]+)\]', decorator)
                if methods_match:
                    methods_str = methods_match.group(1)
                    first_method = re.search(r'["\']([A-Z]+)["\']', methods_str)
                    method = first_method.group(1) if first_method else "GET"
                else:
                    method = "GET"

                return {"method": method, "path": path}

        return None

    def _extract_django_http_method(self, decorators: list[str]) -> Optional[str]:
        """Extract HTTP method from Django decorators."""
        for decorator in decorators:
            if "api_view" in decorator:
                match = re.search(r'["\']([A-Z]+)["\']', decorator)
                if match:
                    return match.group(1)

            if "require_GET" in decorator:
                return "GET"
            if "require_POST" in decorator:
                return "POST"

            if "require_http_methods" in decorator:
                match = re.search(r'["\']([A-Z]+)["\']', decorator)
                if match:
                    return match.group(1)

        return None

    def _extract_model_fields(self, node: ast.ClassDef) -> list[str]:
        """Extract field names from a model class."""
        fields = []

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                if not field_name.startswith('_') and field_name not in ['Config', 'Meta']:
                    fields.append(field_name)

            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_name = target.id
                        if not field_name.startswith('_') and field_name not in ['objects', 'Meta']:
                            fields.append(field_name)

        return fields
