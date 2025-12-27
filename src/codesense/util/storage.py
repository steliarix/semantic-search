"""
Storage module for managing FAISS indexes and metadata.

Handles saving/loading FAISS vector indexes and associated metadata
to/from local filesystem.
"""

import json
import os
import faiss
from pathlib import Path
from typing import Optional


class IndexStorage:
    """
    Manages storage and retrieval of FAISS indexes and metadata.

    Storage format:
        ~/.semantic_search/indexes/{index_name}/
        ├── index.faiss       # FAISS vector index
        └── metadata.json     # File paths, timestamps, etc.
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize storage manager.

        Args:
            base_dir: Base directory for storing indexes.
                     If None, uses ~/.semantic_search/indexes/
        """
        if base_dir is None:
            base_dir = os.path.expanduser("~/.semantic_search/indexes")

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_index_path(self, index_name: str) -> Path:
        """Get the directory path for a specific index."""
        return self.base_dir / index_name

    def get_faiss_path(self, index_name: str) -> Path:
        """Get the FAISS index file path."""
        return self.get_index_path(index_name) / "index.faiss"

    def get_metadata_path(self, index_name: str) -> Path:
        """Get the metadata JSON file path."""
        return self.get_index_path(index_name) / "metadata.json"

    def save_index(
        self,
        index_name: str,
        faiss_index: faiss.Index,
        metadata: dict
    ):
        """
        Save FAISS index and metadata to disk.

        Args:
            index_name: Name of the index
            faiss_index: FAISS index object
            metadata: Dictionary containing file paths, timestamps, etc.
        """
        index_dir = self.get_index_path(index_name)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss_path = self.get_faiss_path(index_name)
        faiss.write_index(faiss_index, str(faiss_path))

        # Save metadata
        metadata_path = self.get_metadata_path(index_name)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"Index saved to: {index_dir}")

    def load_index(self, index_name: str) -> tuple[faiss.Index, dict]:
        """
        Load FAISS index and metadata from disk.

        Args:
            index_name: Name of the index to load

        Returns:
            Tuple of (faiss_index, metadata)

        Raises:
            FileNotFoundError: If index doesn't exist
        """
        faiss_path = self.get_faiss_path(index_name)
        metadata_path = self.get_metadata_path(index_name)

        if not faiss_path.exists():
            raise FileNotFoundError(f"Index '{index_name}' not found at {faiss_path}")

        if not metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata for index '{index_name}' not found at {metadata_path}"
            )

        # Load FAISS index
        faiss_index = faiss.read_index(str(faiss_path))

        # Load metadata
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid metadata JSON for index '{index_name}': {e}")

        return faiss_index, metadata

    def index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists.

        Args:
            index_name: Name of the index

        Returns:
            True if index exists, False otherwise
        """
        return self.get_faiss_path(index_name).exists()

    def list_indexes(self) -> list[str]:
        """
        List all available indexes.

        Returns:
            List of index names
        """
        if not self.base_dir.exists():
            return []

        indexes = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and self.get_faiss_path(item.name).exists():
                indexes.append(item.name)

        return sorted(indexes)

    def delete_index(self, index_name: str):
        """
        Delete an index and its metadata.

        Args:
            index_name: Name of the index to delete
        """
        import shutil

        index_path = self.get_index_path(index_name)
        if index_path.exists():
            shutil.rmtree(index_path)
            print(f"Deleted index: {index_name}")
        else:
            print(f"Index '{index_name}' not found")

    def get_index_info(self, index_name: str) -> dict:
        """
        Get information about an index.

        Args:
            index_name: Name of the index

        Returns:
            Dictionary with index statistics
        """
        if not self.index_exists(index_name):
            raise FileNotFoundError(f"Index '{index_name}' not found")

        faiss_index, metadata = self.load_index(index_name)

        # Check if using chunk-based indexing (v0.2+)
        use_chunking = metadata.get("use_chunking", False)

        # Calculate num_files based on version
        if use_chunking:
            num_files = metadata.get("num_files", 0)
            num_chunks = metadata.get("num_chunks", 0)
        else:
            num_files = len(metadata.get("files", []))
            num_chunks = 0

        result = {
            "name": index_name,
            "num_vectors": faiss_index.ntotal,
            "dimension": faiss_index.d,
            "num_files": num_files,
            "created_at": metadata.get("created_at", "Unknown"),
            "indexed_path": metadata.get("indexed_path", "Unknown"),
        }

        # Add chunk info for v0.2+ indexes
        if use_chunking:
            result["num_chunks"] = num_chunks

        return result
