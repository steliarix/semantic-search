"""
CodeSense - AI-powered semantic code search.

A free, local, and privacy-focused semantic search tool for Python codebases
with intelligent parsing for Django, FastAPI, Flask, and generic Python code.
Uses sentence-transformers for embeddings and FAISS for vector similarity search.
"""

__version__ = "0.4.0"
__author__ = "Artem"
__license__ = "MIT"

from codesense.api import CodeSense, SemanticSearch
from codesense.tools.indexer import Indexer
from codesense.tools.searcher import Searcher, SearchResult
from codesense.util.embeddings import EmbeddingModel
from codesense.util.storage import IndexStorage

__all__ = [
    # High-level API (recommended for library usage)
    "CodeSense",
    "SemanticSearch",
    "SearchResult",
    # Low-level components (for advanced usage)
    "EmbeddingModel",
    "Indexer",
    "Searcher",
    "IndexStorage",
]
