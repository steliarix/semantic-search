"""
Indexer module for building semantic search indexes.

Handles traversing directories, reading Python files, and creating
FAISS indexes with embeddings.
"""

import os
import faiss
from datetime import datetime
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from semantic_search.embeddings import EmbeddingModel
from semantic_search.storage import IndexStorage
from semantic_search.parsers import PythonParser


class Indexer:
    """
    Indexes Python files in a directory for semantic search.
    """

    # Directories to ignore during indexing
    IGNORED_DIRS = {
        '.git', '.svn', '.hg',
        '__pycache__', '.pytest_cache',
        'venv', '.venv', 'env', '.env',
        'node_modules',
        '.idea', '.vscode',
        'build', 'dist', '.eggs', '*.egg-info',
    }

    # File extensions to index
    PYTHON_EXTENSIONS = {'.py'}

    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        storage: Optional[IndexStorage] = None,
        use_chunking: bool = True
    ):
        """
        Initialize the indexer.

        Args:
            embedding_model: EmbeddingModel instance. If None, creates default.
            storage: IndexStorage instance. If None, creates default.
            use_chunking: If True, parse files into chunks (v0.2). If False, index whole files (v0.1).
        """
        self.embedding_model = embedding_model or EmbeddingModel()
        self.storage = storage or IndexStorage()
        self.use_chunking = use_chunking
        self.parser = PythonParser() if use_chunking else None

    def _should_ignore_dir(self, dir_name: str) -> bool:
        """Check if a directory should be ignored."""
        return dir_name in self.IGNORED_DIRS or dir_name.startswith('.')

    def _should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed."""
        return file_path.suffix in self.PYTHON_EXTENSIONS

    def _collect_files(self, root_path: Path) -> list[Path]:
        """
        Recursively collect all Python files to index.

        Args:
            root_path: Root directory to search

        Returns:
            List of Path objects for files to index
        """
        files = []

        for root, dirs, filenames in os.walk(root_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore_dir(d)]

            # Collect Python files
            for filename in filenames:
                file_path = Path(root) / filename
                if self._should_index_file(file_path):
                    files.append(file_path)

        return sorted(files)

    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """
        Read file content safely.

        Args:
            file_path: Path to the file

        Returns:
            File content as string, or None if read fails
        """
        try:
            with open(file_path, encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

    def index_directory(
        self,
        directory_path: str,
        index_name: str,
        show_progress: bool = True
    ):
        """
        Index all Python files in a directory.

        Args:
            directory_path: Path to the directory to index
            index_name: Name for the index
            show_progress: Whether to show progress bar
        """
        root_path = Path(directory_path).resolve()

        if not root_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not root_path.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")

        print(f"Indexing directory: {root_path}")

        # Collect files to index
        files = self._collect_files(root_path)
        print(f"Found {len(files)} Python files")

        if len(files) == 0:
            print("No Python files found to index")
            return

        if self.use_chunking:
            # Use chunk-based indexing (v0.2)
            self._index_with_chunks(root_path, files, index_name, show_progress)
        else:
            # Use whole-file indexing (v0.1)
            self._index_whole_files(root_path, files, index_name, show_progress)

    def _index_with_chunks(
        self,
        root_path: Path,
        files: list[Path],
        index_name: str,
        show_progress: bool
    ):
        """
        Index files using chunk-based parsing (v0.2).

        Args:
            root_path: Root directory path
            files: List of files to index
            index_name: Name for the index
            show_progress: Whether to show progress bar
        """
        # Parse files into chunks
        all_chunks = []
        chunk_texts = []

        for file_path in tqdm(files, desc="Parsing files", disable=not show_progress):
            content = self._read_file_content(file_path)
            if not content:
                continue

            try:
                # Parse file into chunks
                chunks = self.parser.parse(file_path, content)

                for chunk in chunks:
                    # Convert absolute path to relative
                    chunk.file_path = str(Path(chunk.file_path).relative_to(root_path))
                    all_chunks.append(chunk)
                    chunk_texts.append(chunk.get_searchable_text())

            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                continue

        if len(all_chunks) == 0:
            print("No code chunks found to index")
            return

        print(f"Found {len(all_chunks)} code chunks")
        print(f"Creating embeddings for {len(all_chunks)} chunks...")

        # Create embeddings
        embeddings = self.embedding_model.encode(
            chunk_texts,
            show_progress_bar=show_progress
        )

        # Create FAISS index
        dimension = embeddings.shape[1]
        faiss_index = faiss.IndexFlatL2(dimension)
        faiss_index.add(embeddings)

        print(f"Created FAISS index with {faiss_index.ntotal} vectors")

        # Prepare metadata
        metadata = {
            "index_name": index_name,
            "indexed_path": str(root_path),
            "created_at": datetime.now().isoformat(),
            "num_files": len(files),
            "num_chunks": len(all_chunks),
            "embedding_model": self.embedding_model.model_name,
            "embedding_dimension": dimension,
            "use_chunking": True,
            "chunks": [chunk.to_dict() for chunk in all_chunks],
        }

        # Save index
        self.storage.save_index(index_name, faiss_index, metadata)

        print(f"Successfully indexed {len(all_chunks)} chunks from {len(files)} files")

    def _index_whole_files(
        self,
        root_path: Path,
        files: list[Path],
        index_name: str,
        show_progress: bool
    ):
        """
        Index whole files without chunking (v0.1 compatibility).

        Args:
            root_path: Root directory path
            files: List of files to index
            index_name: Name for the index
            show_progress: Whether to show progress bar
        """
        # Read file contents
        file_data = []
        file_contents = []

        for file_path in tqdm(files, desc="Reading files", disable=not show_progress):
            content = self._read_file_content(file_path)
            if content:
                file_data.append({
                    "file_path": str(file_path.relative_to(root_path)),
                    "absolute_path": str(file_path),
                    "size": len(content),
                    "timestamp": datetime.now().isoformat(),
                })
                file_contents.append(content)

        if len(file_contents) == 0:
            print("No valid files to index")
            return

        print(f"Creating embeddings for {len(file_contents)} files...")

        # Create embeddings
        embeddings = self.embedding_model.encode(
            file_contents,
            show_progress_bar=show_progress
        )

        # Create FAISS index
        dimension = embeddings.shape[1]
        faiss_index = faiss.IndexFlatL2(dimension)
        faiss_index.add(embeddings)

        print(f"Created FAISS index with {faiss_index.ntotal} vectors")

        # Prepare metadata
        metadata = {
            "index_name": index_name,
            "indexed_path": str(root_path),
            "created_at": datetime.now().isoformat(),
            "num_files": len(file_data),
            "embedding_model": self.embedding_model.model_name,
            "embedding_dimension": dimension,
            "use_chunking": False,
            "files": file_data,
        }

        # Save index
        self.storage.save_index(index_name, faiss_index, metadata)

        print(f"Successfully indexed {len(file_data)} files")

    def index_files(
        self,
        file_paths: list[str],
        index_name: str,
        show_progress: bool = True
    ):
        """
        Index specific files (for future use).

        Args:
            file_paths: List of file paths to index
            index_name: Name for the index
            show_progress: Whether to show progress bar
        """
        # TODO: Implement for v0.3 (incremental updates)
        raise NotImplementedError("Indexing specific files not yet implemented")
