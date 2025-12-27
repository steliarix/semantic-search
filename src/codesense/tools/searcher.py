"""
Searcher module for semantic search.

Handles loading indexes and performing similarity search queries.
"""

from dataclasses import dataclass
from typing import Optional

from codesense.util.embeddings import EmbeddingModel
from codesense.util.storage import IndexStorage


@dataclass
class SearchResult:
    """
    Represents a single search result.

    For v0.2 chunk-based results, includes additional fields like
    chunk_type, name, start_line, end_line, signature, etc.
    """
    file_path: str
    score: float
    rank: int

    # Optional fields for chunk-based results (v0.2)
    chunk_type: Optional[str] = None  # function, class, method
    name: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parent: Optional[str] = None

    # Framework-specific fields (v0.4)
    framework_type: Optional[str] = None  # django_model, fastapi_route, etc.
    http_method: Optional[str] = None
    route_path: Optional[str] = None

    # Legacy fields (v0.1 compatibility)
    absolute_path: Optional[str] = None
    size: Optional[int] = None

    def __str__(self) -> str:
        if self.chunk_type:
            # v0.2 chunk-based format
            location = f"{self.file_path}:{self.start_line}"
            if self.parent:
                context = f"{self.parent}.{self.name}"
            else:
                context = self.name
            return f"[{self.rank}] {self.chunk_type}: {context} ({location}) - Score: {self.score:.4f}"
        else:
            # v0.1 whole-file format
            return f"[{self.rank}] {self.file_path} (score: {self.score:.4f})"


class Searcher:
    """
    Performs semantic search over indexed files.
    """

    def __init__(
        self,
        index_name: str,
        embedding_model: Optional[EmbeddingModel] = None,
        storage: Optional[IndexStorage] = None
    ):
        """
        Initialize the searcher.

        Args:
            index_name: Name of the index to search
            embedding_model: EmbeddingModel instance. If None, creates default.
            storage: IndexStorage instance. If None, creates default.
        """
        self.index_name = index_name
        self.storage = storage or IndexStorage()

        # Load index and metadata
        self.faiss_index, self.metadata = self.storage.load_index(index_name)

        # Initialize embedding model
        # Use the same model that was used for indexing
        model_name = self.metadata.get("embedding_model", EmbeddingModel.DEFAULT_MODEL)
        self.embedding_model = embedding_model or EmbeddingModel(model_name=model_name)

        print(f"Loaded index '{index_name}' with {self.faiss_index.ntotal} vectors")

    def search(self, query: str, top_k: int = 5, filter_type: Optional[str] = None) -> list[SearchResult]:
        """
        Search for files/chunks semantically similar to the query.

        Uses smart query analysis to auto-detect intent and boost relevant results.

        Args:
            query: Search query text
            top_k: Number of top results to return
            filter_type: Filter results by framework type (e.g., 'model', 'route', 'view')

        Returns:
            List of SearchResult objects, ordered by relevance
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        # Check if index is empty
        if self.faiss_index.ntotal == 0:
            return []

        # Smart query analysis - detect intent from query
        detected_filter = self._analyze_query_intent(query) if not filter_type else None
        active_filter = filter_type or detected_filter

        # Create embedding for the query
        query_embedding = self.embedding_model.encode([query], show_progress_bar=False)

        # When filtering (explicit or auto-detected), we need to search more results initially
        search_k = top_k * 10 if active_filter else top_k
        actual_k = min(search_k, self.faiss_index.ntotal)

        # Search in FAISS index
        # Returns: distances (lower = more similar), indices
        distances, indices = self.faiss_index.search(query_embedding, actual_k)

        # Check if using chunk-based indexing
        use_chunking = self.metadata.get("use_chunking", False)

        # Convert to SearchResult objects
        results = []

        if use_chunking:
            # v0.2 chunk-based results
            chunks = self.metadata.get("chunks", [])

            for distance, idx in zip(distances[0], indices[0]):
                # Skip invalid indices
                if idx >= 0 and idx < len(chunks):
                    chunk_info = chunks[idx]

                    # Apply filter if specified (explicit or auto-detected)
                    if active_filter and not self._matches_filter(chunk_info, active_filter):
                        continue

                    # Smart boosting - if auto-detected filter, boost matching types
                    boosted_score = float(distance)
                    if detected_filter and self._matches_filter(chunk_info, detected_filter):
                        boosted_score *= 0.8  # 20% boost for matching detected intent

                    result = SearchResult(
                        file_path=chunk_info["file_path"],
                        score=boosted_score,
                        rank=0,  # Will be set later
                        chunk_type=chunk_info.get("type"),
                        name=chunk_info.get("name"),
                        start_line=chunk_info.get("start_line"),
                        end_line=chunk_info.get("end_line"),
                        signature=chunk_info.get("signature"),
                        docstring=chunk_info.get("docstring"),
                        parent=chunk_info.get("parent"),
                        framework_type=chunk_info.get("framework_type"),
                        http_method=chunk_info.get("http_method"),
                        route_path=chunk_info.get("route_path"),
                    )
                    results.append(result)

                    # Stop if we have enough filtered results
                    if len(results) >= top_k:
                        break

            # Sort by boosted score and assign ranks
            results.sort(key=lambda r: r.score)
            for rank, result in enumerate(results, start=1):
                result.rank = rank
        else:
            # v0.1 whole-file results
            files = self.metadata.get("files", [])

            for rank, (distance, idx) in enumerate(zip(distances[0], indices[0]), start=1):
                # Skip invalid indices
                if idx >= 0 and idx < len(files):
                    file_info = files[idx]
                    result = SearchResult(
                        file_path=file_info["file_path"],
                        score=float(distance),
                        rank=rank,
                        absolute_path=file_info.get("absolute_path", ""),
                        size=file_info.get("size", 0)
                    )
                    results.append(result)

        return results

    def _analyze_query_intent(self, query: str) -> Optional[str]:
        """
        Analyze query to detect user intent and auto-suggest filter.

        Args:
            query: Search query text

        Returns:
            Detected filter type or None
        """
        query_lower = query.lower()

        # Intent keywords mapping
        intent_keywords = {
            "model": ["model", "models", "schema", "schemas", "entity", "entities", "orm", "database table"],
            "route": ["route", "routes", "endpoint", "endpoints", "api", "path", "url"],
            "view": ["view", "views", "viewset", "viewsets", "template"],
            "serializer": ["serializer", "serializers"],
            "function": ["function", "def ", "method", "methods"],
            "class": ["class", "classes"],
        }

        # Framework-specific keywords
        framework_keywords = {
            "django": ["django", "drf", "rest_framework"],
            "fastapi": ["fastapi", "pydantic"],
            "flask": ["flask", "blueprint"],
        }

        # Check for framework-specific intent
        for framework, keywords in framework_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return framework

        # Check for type-specific intent
        for intent, keywords in intent_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent

        return None

    def _matches_filter(self, chunk_info: dict, filter_type: str) -> bool:
        """
        Check if a chunk matches the filter criteria.

        Args:
            chunk_info: Chunk metadata dictionary
            filter_type: Filter type (e.g., 'model', 'route', 'view')

        Returns:
            True if the chunk matches the filter
        """
        framework_type = chunk_info.get("framework_type", "")
        chunk_type = chunk_info.get("type", "")

        # Map filter types to framework types (universal mapping)
        filter_mappings = {
            "model": ["django_model", "pydantic_model"],
            "route": ["fastapi_route", "flask_route"],
            "view": ["django_view"],
            "serializer": ["django_serializer"],
            "function": ["function"],
            "class": ["class"],
            "method": ["method"],
            # Framework-specific filters
            "django": ["django_model", "django_view", "django_serializer"],
            "fastapi": ["fastapi_route", "pydantic_model"],
            "flask": ["flask_route", "flask_blueprint"],
            # Specific framework types
            "django_model": ["django_model"],
            "django_view": ["django_view"],
            "django_serializer": ["django_serializer"],
            "fastapi_route": ["fastapi_route"],
            "flask_route": ["flask_route"],
            "pydantic_model": ["pydantic_model"],
        }

        # Check if filter_type matches
        filter_lower = filter_type.lower()
        if filter_lower in filter_mappings:
            allowed_types = filter_mappings[filter_lower]
            return framework_type in allowed_types or chunk_type in allowed_types

        # Check for partial matches (e.g., "api" matches "fastapi_route", "django_view")
        if filter_lower in framework_type.lower() or filter_lower in chunk_type.lower():
            return True

        # Direct framework_type or chunk_type match
        return framework_type == filter_type or chunk_type == filter_type

    def get_index_info(self) -> dict:
        """
        Get information about the loaded index.

        Returns:
            Dictionary with index statistics
        """
        return {
            "index_name": self.index_name,
            "num_vectors": self.faiss_index.ntotal,
            "dimension": self.faiss_index.d,
            "num_files": len(self.metadata.get("files", [])),
            "created_at": self.metadata.get("created_at"),
            "indexed_path": self.metadata.get("indexed_path"),
            "embedding_model": self.metadata.get("embedding_model"),
        }

    def print_results(self, results: list[SearchResult], show_preview: bool = False):
        """
        Print search results in a readable format.

        Args:
            results: List of SearchResult objects
            show_preview: Whether to show code preview
        """
        if not results:
            print("No results found")
            return

        print(f"\nFound {len(results)} results:\n")

        for result in results:
            print(f"  {result}")

            # Show additional details for chunk-based results
            if result.chunk_type and show_preview:
                if result.signature:
                    print(f"      Signature: {result.signature}")
                if result.docstring:
                    # Show first line of docstring
                    first_line = result.docstring.split('\n')[0]
                    print(f"      Doc: {first_line}")
                print()

        print()
