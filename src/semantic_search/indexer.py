"""
Indexer module for building semantic search indexes.

Handles traversing directories, reading Python files, and creating
FAISS indexes with embeddings.
"""

import os
import hashlib
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

    def _calculate_file_hash(self, content: str) -> str:
        """
        Calculate SHA256 hash of file content.

        Args:
            content: File content as string

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _get_file_mtime(self, file_path: Path) -> float:
        """
        Get file modification timestamp.

        Args:
            file_path: Path to the file

        Returns:
            Modification timestamp
        """
        return file_path.stat().st_mtime

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
        file_metadata = {}  # Store file hash and mtime for each file

        for file_path in tqdm(files, desc="Parsing files", disable=not show_progress):
            content = self._read_file_content(file_path)
            if not content:
                continue

            try:
                # Calculate file hash and mtime
                file_hash = self._calculate_file_hash(content)
                mtime = self._get_file_mtime(file_path)
                rel_path = str(file_path.relative_to(root_path))

                # Store file metadata
                file_metadata[rel_path] = {
                    "hash": file_hash,
                    "mtime": mtime,
                    "size": len(content)
                }

                # Parse file into chunks
                chunks = self.parser.parse(file_path, content)

                for chunk in chunks:
                    # Convert absolute path to relative
                    chunk.file_path = rel_path
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
            "updated_at": datetime.now().isoformat(),
            "num_files": len(files),
            "num_chunks": len(all_chunks),
            "embedding_model": self.embedding_model.model_name,
            "embedding_dimension": dimension,
            "use_chunking": True,
            "chunks": [chunk.to_dict() for chunk in all_chunks],
            "file_metadata": file_metadata,  # v0.3: file hashes and mtimes
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
                    "hash": self._calculate_file_hash(content),
                    "mtime": self._get_file_mtime(file_path),
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
            "updated_at": datetime.now().isoformat(),
            "num_files": len(file_data),
            "embedding_model": self.embedding_model.model_name,
            "embedding_dimension": dimension,
            "use_chunking": False,
            "files": file_data,
        }

        # Save index
        self.storage.save_index(index_name, faiss_index, metadata)

        print(f"Successfully indexed {len(file_data)} files")

    def update_index(
        self,
        index_name: str,
        show_progress: bool = True
    ):
        """
        Update an existing index incrementally (v0.3).

        Only re-indexes files that have changed, adds new files,
        and removes deleted files from the index.

        Args:
            index_name: Name of the index to update
            show_progress: Whether to show progress bar

        Raises:
            FileNotFoundError: If index doesn't exist
        """
        print(f"Updating index: {index_name}")

        # Load existing index
        if not self.storage.index_exists(index_name):
            raise FileNotFoundError(f"Index '{index_name}' does not exist")

        faiss_index, metadata = self.storage.load_index(index_name)

        # Get indexed path
        indexed_path = Path(metadata["indexed_path"])
        if not indexed_path.exists():
            raise FileNotFoundError(f"Indexed directory not found: {indexed_path}")

        use_chunking = metadata.get("use_chunking", False)

        if use_chunking:
            self._update_index_with_chunks(index_name, indexed_path, faiss_index, metadata, show_progress)
        else:
            self._update_index_whole_files(index_name, indexed_path, faiss_index, metadata, show_progress)

    def _update_index_with_chunks(
        self,
        index_name: str,
        root_path: Path,
        faiss_index: faiss.Index,
        metadata: dict,
        show_progress: bool
    ):
        """
        Update chunk-based index (v0.2+).

        Args:
            index_name: Name of the index
            root_path: Root directory path
            faiss_index: Existing FAISS index
            metadata: Existing metadata
            show_progress: Whether to show progress bar
        """
        # Get current files in directory
        current_files = {str(f.relative_to(root_path)): f for f in self._collect_files(root_path)}

        # Get existing file metadata
        existing_file_metadata = metadata.get("file_metadata", {})

        # Get existing chunks
        existing_chunks = metadata.get("chunks", [])

        # Determine which files need updating
        new_files = []
        changed_files = []
        deleted_files = []

        # Check for new and changed files
        for rel_path, abs_path in current_files.items():
            if rel_path not in existing_file_metadata:
                # New file
                new_files.append(abs_path)
            else:
                # Check if file changed
                content = self._read_file_content(abs_path)
                if content:
                    current_hash = self._calculate_file_hash(content)
                    existing_hash = existing_file_metadata[rel_path].get("hash", "")

                    if current_hash != existing_hash:
                        changed_files.append(abs_path)

        # Check for deleted files
        for rel_path in existing_file_metadata.keys():
            if rel_path not in current_files:
                deleted_files.append(rel_path)

        print(f"Files analysis:")
        print(f"  New: {len(new_files)}")
        print(f"  Changed: {len(changed_files)}")
        print(f"  Deleted: {len(deleted_files)}")
        print(f"  Unchanged: {len(current_files) - len(new_files) - len(changed_files)}")

        # If nothing changed, we're done
        if not new_files and not changed_files and not deleted_files:
            print("No changes detected. Index is up to date.")
            metadata["updated_at"] = datetime.now().isoformat()
            self.storage.save_index(index_name, faiss_index, metadata)
            return

        # Remove chunks from deleted and changed files
        files_to_remove = set(deleted_files + [str(f.relative_to(root_path)) for f in changed_files])

        # Keep only chunks from unchanged files
        kept_chunks = []
        kept_chunk_indices = []

        for idx, chunk_dict in enumerate(existing_chunks):
            if chunk_dict["file_path"] not in files_to_remove:
                kept_chunks.append(chunk_dict)
                kept_chunk_indices.append(idx)

        print(f"Keeping {len(kept_chunks)} chunks from unchanged files")

        # Parse new and changed files
        files_to_index = new_files + changed_files
        new_chunks = []
        new_chunk_texts = []
        new_file_metadata = {}

        for file_path in tqdm(files_to_index, desc="Parsing files", disable=not show_progress):
            content = self._read_file_content(file_path)
            if not content:
                continue

            try:
                # Calculate file hash and mtime
                file_hash = self._calculate_file_hash(content)
                mtime = self._get_file_mtime(file_path)
                rel_path = str(file_path.relative_to(root_path))

                # Store file metadata
                new_file_metadata[rel_path] = {
                    "hash": file_hash,
                    "mtime": mtime,
                    "size": len(content)
                }

                # Parse file into chunks
                chunks = self.parser.parse(file_path, content)

                for chunk in chunks:
                    chunk.file_path = rel_path
                    new_chunks.append(chunk)
                    new_chunk_texts.append(chunk.get_searchable_text())

            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                continue

        print(f"Parsed {len(new_chunks)} new chunks")

        # Rebuild FAISS index with kept + new chunks
        all_chunks = kept_chunks + [chunk.to_dict() for chunk in new_chunks]

        # If we have kept chunks, get their embeddings from old index
        if kept_chunk_indices:
            kept_embeddings = faiss_index.reconstruct_n(0, faiss_index.ntotal)
            kept_embeddings = kept_embeddings[kept_chunk_indices]
        else:
            kept_embeddings = None

        # Create embeddings for new chunks
        if new_chunk_texts:
            print(f"Creating embeddings for {len(new_chunk_texts)} new chunks...")
            new_embeddings = self.embedding_model.encode(
                new_chunk_texts,
                show_progress_bar=show_progress
            )
        else:
            new_embeddings = None

        # Combine embeddings
        import numpy as np
        if kept_embeddings is not None and new_embeddings is not None:
            combined_embeddings = np.vstack([kept_embeddings, new_embeddings])
        elif kept_embeddings is not None:
            combined_embeddings = kept_embeddings
        elif new_embeddings is not None:
            combined_embeddings = new_embeddings
        else:
            print("No embeddings to index")
            return

        # Create new FAISS index
        dimension = combined_embeddings.shape[1]
        new_faiss_index = faiss.IndexFlatL2(dimension)
        new_faiss_index.add(combined_embeddings)

        print(f"Updated FAISS index: {new_faiss_index.ntotal} vectors")

        # Update file metadata (keep unchanged + add new)
        updated_file_metadata = {k: v for k, v in existing_file_metadata.items() if k not in files_to_remove}
        updated_file_metadata.update(new_file_metadata)

        # Update metadata
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["num_files"] = len(updated_file_metadata)
        metadata["num_chunks"] = len(all_chunks)
        metadata["chunks"] = all_chunks
        metadata["file_metadata"] = updated_file_metadata

        # Save updated index
        self.storage.save_index(index_name, new_faiss_index, metadata)

        print(f"Successfully updated index '{index_name}'")
        print(f"  Total files: {len(updated_file_metadata)}")
        print(f"  Total chunks: {len(all_chunks)}")

    def _update_index_whole_files(
        self,
        index_name: str,
        root_path: Path,
        faiss_index: faiss.Index,
        metadata: dict,
        show_progress: bool
    ):
        """
        Update whole-file index (v0.1 compatibility).

        Args:
            index_name: Name of the index
            root_path: Root directory path
            faiss_index: Existing FAISS index
            metadata: Existing metadata
            show_progress: Whether to show progress bar
        """
        # Get current files in directory
        current_files = {str(f.relative_to(root_path)): f for f in self._collect_files(root_path)}

        # Get existing files from metadata
        existing_files = {f["file_path"]: f for f in metadata.get("files", [])}

        # Determine which files need updating
        new_files = []
        changed_files = []
        deleted_file_paths = []

        # Check for new and changed files
        for rel_path, abs_path in current_files.items():
            if rel_path not in existing_files:
                # New file
                new_files.append(abs_path)
            else:
                # Check if file changed
                content = self._read_file_content(abs_path)
                if content:
                    current_hash = self._calculate_file_hash(content)
                    existing_hash = existing_files[rel_path].get("hash", "")

                    if current_hash != existing_hash:
                        changed_files.append(abs_path)

        # Check for deleted files
        for rel_path in existing_files.keys():
            if rel_path not in current_files:
                deleted_file_paths.append(rel_path)

        print(f"Files analysis:")
        print(f"  New: {len(new_files)}")
        print(f"  Changed: {len(changed_files)}")
        print(f"  Deleted: {len(deleted_file_paths)}")
        print(f"  Unchanged: {len(current_files) - len(new_files) - len(changed_files)}")

        # If nothing changed, we're done
        if not new_files and not changed_files and not deleted_file_paths:
            print("No changes detected. Index is up to date.")
            metadata["updated_at"] = datetime.now().isoformat()
            self.storage.save_index(index_name, faiss_index, metadata)
            return

        # Remove deleted and changed files
        files_to_remove = set(deleted_file_paths + [str(f.relative_to(root_path)) for f in changed_files])

        # Keep only unchanged files
        kept_files = []
        kept_file_indices = []

        files_list = metadata.get("files", [])
        for idx, file_dict in enumerate(files_list):
            if file_dict["file_path"] not in files_to_remove:
                kept_files.append(file_dict)
                kept_file_indices.append(idx)

        print(f"Keeping {len(kept_files)} unchanged files")

        # Read new and changed files
        files_to_index = new_files + changed_files
        new_file_data = []
        new_file_contents = []

        for file_path in tqdm(files_to_index, desc="Reading files", disable=not show_progress):
            content = self._read_file_content(file_path)
            if content:
                new_file_data.append({
                    "file_path": str(file_path.relative_to(root_path)),
                    "absolute_path": str(file_path),
                    "size": len(content),
                    "timestamp": datetime.now().isoformat(),
                    "hash": self._calculate_file_hash(content),
                    "mtime": self._get_file_mtime(file_path),
                })
                new_file_contents.append(content)

        print(f"Read {len(new_file_contents)} new/changed files")

        # Rebuild FAISS index with kept + new files
        all_files = kept_files + new_file_data

        # If we have kept files, get their embeddings from old index
        if kept_file_indices:
            kept_embeddings = faiss_index.reconstruct_n(0, faiss_index.ntotal)
            kept_embeddings = kept_embeddings[kept_file_indices]
        else:
            kept_embeddings = None

        # Create embeddings for new files
        if new_file_contents:
            print(f"Creating embeddings for {len(new_file_contents)} files...")
            new_embeddings = self.embedding_model.encode(
                new_file_contents,
                show_progress_bar=show_progress
            )
        else:
            new_embeddings = None

        # Combine embeddings
        import numpy as np
        if kept_embeddings is not None and new_embeddings is not None:
            combined_embeddings = np.vstack([kept_embeddings, new_embeddings])
        elif kept_embeddings is not None:
            combined_embeddings = kept_embeddings
        elif new_embeddings is not None:
            combined_embeddings = new_embeddings
        else:
            print("No embeddings to index")
            return

        # Create new FAISS index
        dimension = combined_embeddings.shape[1]
        new_faiss_index = faiss.IndexFlatL2(dimension)
        new_faiss_index.add(combined_embeddings)

        print(f"Updated FAISS index: {new_faiss_index.ntotal} vectors")

        # Update metadata
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["num_files"] = len(all_files)
        metadata["files"] = all_files

        # Save updated index
        self.storage.save_index(index_name, new_faiss_index, metadata)

        print(f"Successfully updated index '{index_name}'")
        print(f"  Total files: {len(all_files)}")
