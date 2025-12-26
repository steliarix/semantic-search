"""
Semantic Search - Local semantic search for Python projects.

A free, local, and privacy-focused semantic search tool for Python codebases
(Django, FastAPI). Uses sentence-transformers for embeddings and FAISS for
vector similarity search.
"""

__version__ = "0.2.0"
__author__ = "Artem"
__license__ = "MIT"

from semantic_search.embeddings import EmbeddingModel
from semantic_search.indexer import Indexer
from semantic_search.searcher import Searcher
from semantic_search.storage import IndexStorage

__all__ = [
    "EmbeddingModel",
    "Indexer",
    "Searcher",
    "IndexStorage",
]
