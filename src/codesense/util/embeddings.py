"""
Embedding model wrapper for sentence-transformers.

Handles loading and encoding text into vector embeddings using
pre-trained models from sentence-transformers library.
"""

import numpy as np
from typing import Union
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """
    Wrapper for sentence-transformers models.

    Provides a simple interface for encoding text into embeddings.
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = None):
        """
        Initialize the embedding model.

        Args:
            model_name: Name of the sentence-transformers model to use.
                       If None, uses DEFAULT_MODEL.
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the sentence-transformers model."""
        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print(f"Model loaded. Embedding dimension: {self.get_embedding_dim()}")

    def encode(
        self,
        texts: Union[str, list[str]],
        show_progress_bar: bool = True
    ) -> np.ndarray:
        """
        Encode text(s) into embeddings.

        Args:
            texts: Single text string or list of text strings to encode.
            show_progress_bar: Whether to show progress bar during encoding.

        Returns:
            numpy array of embeddings. Shape: (n_texts, embedding_dim)
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(
            texts,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=True
        )

        return embeddings

    def get_embedding_dim(self) -> int:
        """
        Get the dimension of embeddings produced by this model.

        Returns:
            Embedding dimension (e.g., 384 for all-MiniLM-L6-v2)
        """
        return self.model.get_sentence_embedding_dimension()

    def __repr__(self) -> str:
        return f"EmbeddingModel(model_name='{self.model_name}', dim={self.get_embedding_dim()})"
