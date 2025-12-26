"""
Searcher module for semantic search.

Handles loading indexes and performing similarity search queries.
"""

from dataclasses import dataclass
from typing import Optional

from semantic_search.embeddings import EmbeddingModel
from semantic_search.storage import IndexStorage


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

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """
        Search for files/chunks semantically similar to the query.

        Args:
            query: Search query text
            top_k: Number of top results to return

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

        # Create embedding for the query
        query_embedding = self.embedding_model.encode([query], show_progress_bar=False)

        # Adjust top_k if it exceeds available vectors
        actual_k = min(top_k, self.faiss_index.ntotal)

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

            for rank, (distance, idx) in enumerate(zip(distances[0], indices[0]), start=1):
                # Skip invalid indices
                if idx >= 0 and idx < len(chunks):
                    chunk_info = chunks[idx]
                    result = SearchResult(
                        file_path=chunk_info["file_path"],
                        score=float(distance),
                        rank=rank,
                        chunk_type=chunk_info.get("type"),
                        name=chunk_info.get("name"),
                        start_line=chunk_info.get("start_line"),
                        end_line=chunk_info.get("end_line"),
                        signature=chunk_info.get("signature"),
                        docstring=chunk_info.get("docstring"),
                        parent=chunk_info.get("parent"),
                    )
                    results.append(result)
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
