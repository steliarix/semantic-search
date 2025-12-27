"""
Python API for programmatic access to CodeSense.

Provides high-level classes for using CodeSense as a library in your code.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from codesense.tools.indexer import Indexer
from codesense.tools.searcher import Searcher, SearchResult
from codesense.util.storage import IndexStorage
from codesense.util.embeddings import EmbeddingModel


class CodeSense:
    """
    Main API class for CodeSense semantic search.

    Provides programmatic access to indexing and searching functionality.

    Example:
        >>> from codesense import CodeSense
        >>>
        >>> # Initialize with index name
        >>> cs = CodeSense(index_name="my_project")
        >>>
        >>> # Index a directory
        >>> cs.index("/path/to/project")
        >>>
        >>> # Search
        >>> results = cs.search("user authentication", top_k=5)
        >>> for result in results:
        ...     print(f"{result.file_path}:{result.start_line}")
        ...     print(f"Score: {result.score}")
    """

    def __init__(
        self,
        index_name: str,
        embedding_model: Optional[str] = None,
        storage_path: Optional[str] = None
    ):
        """
        Initialize CodeSense API.

        Args:
            index_name: Name of the index to use/create
            embedding_model: Name of the embedding model (default: all-MiniLM-L6-v2)
            storage_path: Custom storage path for indexes (default: ~/.codesense/indexes)
        """
        self.index_name = index_name
        self._embedding_model_name = embedding_model
        self._storage_path = storage_path

        # Lazy initialization
        self._indexer: Optional[Indexer] = None
        self._searcher: Optional[Searcher] = None
        self._storage: Optional[IndexStorage] = None
        self._embedding_model: Optional[EmbeddingModel] = None

    @property
    def storage(self) -> IndexStorage:
        """Get or create storage instance."""
        if self._storage is None:
            if self._storage_path:
                self._storage = IndexStorage(base_path=Path(self._storage_path))
            else:
                self._storage = IndexStorage()
        return self._storage

    @property
    def embedding_model(self) -> EmbeddingModel:
        """Get or create embedding model instance."""
        if self._embedding_model is None:
            if self._embedding_model_name:
                self._embedding_model = EmbeddingModel(model_name=self._embedding_model_name)
            else:
                self._embedding_model = EmbeddingModel()
        return self._embedding_model

    def index(
        self,
        directory: str,
        show_progress: bool = False,
        use_chunking: bool = True
    ) -> None:
        """
        Index a directory of Python files.

        Automatically detects Django, FastAPI, Flask, and generic Python code.

        Args:
            directory: Path to directory to index
            show_progress: Whether to show progress bar
            use_chunking: Whether to use chunk-based parsing (recommended)

        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If directory is not valid

        Example:
            >>> cs = CodeSense(index_name="my_app")
            >>> cs.index("/path/to/django/project")
        """
        indexer = Indexer(
            embedding_model=self.embedding_model,
            storage=self.storage,
            use_chunking=use_chunking
        )
        indexer.index_directory(directory, self.index_name, show_progress=show_progress)

        # Reset searcher to reload the new index
        self._searcher = None

    def update(self, show_progress: bool = False) -> None:
        """
        Update existing index incrementally.

        Only re-indexes files that have changed.

        Args:
            show_progress: Whether to show progress bar

        Raises:
            FileNotFoundError: If index doesn't exist

        Example:
            >>> cs = CodeSense(index_name="my_app")
            >>> cs.update()
        """
        indexer = Indexer(
            embedding_model=self.embedding_model,
            storage=self.storage
        )
        indexer.update_index(self.index_name, show_progress=show_progress)

        # Reset searcher to reload the updated index
        self._searcher = None

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_type: Optional[str] = None,
        auto_update: bool = False
    ) -> List[SearchResult]:
        """
        Search for code semantically similar to the query.

        Uses smart query analysis to auto-detect intent and boost relevant results.

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_type: Filter by type (model, route, view, django, fastapi, flask)
            auto_update: Whether to update index before searching

        Returns:
            List of SearchResult objects

        Raises:
            FileNotFoundError: If index doesn't exist
            ValueError: If query is empty or top_k is invalid

        Example:
            >>> cs = CodeSense(index_name="my_app")
            >>> results = cs.search("user authentication logic", top_k=5)
            >>> for result in results:
            ...     print(f"[{result.rank}] {result.file_path}:{result.start_line}")
            ...     print(f"  {result.signature}")
            ...     print(f"  Score: {result.score:.4f}")
        """
        # Auto-update if requested
        if auto_update:
            try:
                self.update(show_progress=False)
            except Exception:
                pass  # Continue with existing index if update fails

        # Lazy load searcher
        if self._searcher is None:
            self._searcher = Searcher(
                index_name=self.index_name,
                embedding_model=self.embedding_model,
                storage=self.storage
            )

        return self._searcher.search(query, top_k=top_k, filter_type=filter_type)

    def delete(self) -> None:
        """
        Delete the index.

        Example:
            >>> cs = CodeSense(index_name="old_project")
            >>> cs.delete()
        """
        self.storage.delete_index(self.index_name)
        self._searcher = None

    def exists(self) -> bool:
        """
        Check if the index exists.

        Returns:
            True if index exists, False otherwise

        Example:
            >>> cs = CodeSense(index_name="my_app")
            >>> if not cs.exists():
            ...     cs.index("/path/to/project")
        """
        return self.storage.index_exists(self.index_name)

    def info(self) -> Dict[str, Any]:
        """
        Get information about the index.

        Returns:
            Dictionary with index statistics

        Raises:
            FileNotFoundError: If index doesn't exist

        Example:
            >>> cs = CodeSense(index_name="my_app")
            >>> info = cs.info()
            >>> print(f"Files: {info['num_files']}")
            >>> print(f"Chunks: {info.get('num_chunks', 'N/A')}")
            >>> print(f"Created: {info['created_at']}")
        """
        if not self.exists():
            raise FileNotFoundError(f"Index '{self.index_name}' does not exist")

        info_dict = self.storage.get_index_info(self.index_name)
        # Add index_name for consistency (storage returns "name")
        info_dict['index_name'] = self.index_name
        return info_dict

    @staticmethod
    def list_indexes(storage_path: Optional[str] = None) -> List[str]:
        """
        List all available indexes.

        Args:
            storage_path: Custom storage path (default: ~/.codesense/indexes)

        Returns:
            List of index names

        Example:
            >>> from codesense import CodeSense
            >>> indexes = CodeSense.list_indexes()
            >>> for name in indexes:
            ...     print(name)
        """
        if storage_path:
            storage = IndexStorage(base_path=Path(storage_path))
        else:
            storage = IndexStorage()

        return storage.list_indexes()

    @staticmethod
    def get_all_index_info(storage_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all indexes.

        Args:
            storage_path: Custom storage path (default: ~/.codesense/indexes)

        Returns:
            Dictionary mapping index names to their info

        Example:
            >>> from codesense import CodeSense
            >>> all_info = CodeSense.get_all_index_info()
            >>> for name, info in all_info.items():
            ...     print(f"{name}: {info['num_files']} files")
        """
        if storage_path:
            storage = IndexStorage(base_path=Path(storage_path))
        else:
            storage = IndexStorage()

        indexes = storage.list_indexes()
        result = {}

        for index_name in indexes:
            try:
                result[index_name] = storage.get_index_info(index_name)
            except Exception:
                # Skip indexes that can't be loaded
                continue

        return result


# Convenience alias
SemanticSearch = CodeSense


__all__ = [
    'CodeSense',
    'SemanticSearch',
    'SearchResult',
]
