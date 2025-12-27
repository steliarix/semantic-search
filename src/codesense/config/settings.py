"""Default settings and configuration for codesense."""

# Default embedding model
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Default index directory
DEFAULT_INDEX_DIR = ".codesense_index"

# Supported file extensions
SUPPORTED_EXTENSIONS = {".py"}

# Chunk size for parsing
DEFAULT_CHUNK_SIZE = 512

# Maximum context length
MAX_CONTEXT_LENGTH = 2048
