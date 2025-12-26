# Semantic Search

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Local, free semantic search for Python projects (Django, FastAPI, and more).

## Features

- **Free** - No API keys or paid services required
- **Local** - All data stored on your machine
- **Private** - Complete confidentiality of your code
- **Offline** - Works without internet connection (after initial model download)
- **Fast** - Optimized with FAISS for vector search
- **Chunk-based** (v0.2+) - Search functions, classes, and methods separately
- **Smart parsing** - AST-based code extraction with signatures and docstrings
- **Precise results** - File:line locations for exact code navigation
- **Preview by default** - Automatically shows signatures and docstrings in results
- **Incremental updates** (v0.3+) - Update only changed files, 10x faster than full re-indexing

## Technologies

- **sentence-transformers** - For creating embeddings
- **FAISS** - For vector similarity search
- **Click** - CLI interface

## Installation

### From PyPI (when published)

```bash
pip install semantic-search
```

### From Source

```bash
# Clone repository
git clone https://github.com/steliarix/semantic-search.git
cd semantic-search

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .
```

## Quick Start

```bash
# 1. Index your project
semantic-search index ~/projects/my-django-app --name django_app

# 2. Search
semantic-search search "user authentication" --index django_app

# 3. Make code changes, then update index (only changed files)
semantic-search update django_app

# 4. View indexes
semantic-search list
```

## Usage

### Indexing a Project

Index a directory containing Python code:

```bash
semantic-search index /path/to/your/project --name my_project
```

Example:

```bash
semantic-search index ~/projects/django-app --name django_app
```

### Updating an Index

Update an existing index incrementally (only re-index changed files):

```bash
semantic-search update my_project
```

This will:
- Detect new, changed, and deleted files
- Re-index only changed files
- Preserve embeddings for unchanged files
- 10x faster than full re-indexing

### Searching

Search semantically across your indexed code:

```bash
semantic-search search "user authentication logic" --index my_project
```

Example queries:

```bash
# Search for authentication functions (preview enabled by default)
semantic-search search "user login and authentication" --index django_app

# Search for database models
semantic-search search "database models for users" --index django_app

# Search for API endpoints
semantic-search search "REST API endpoints" --index fastapi_app

# More results
semantic-search search "payment processing" --index my_project --top-k 10

# Auto-update index before searching (v0.3+)
semantic-search search "user authentication" --index django_app --auto-update

# Disable preview mode if needed
semantic-search search "user authentication" --index django_app --no-preview
```

### List Indexes

View all created indexes:

```bash
semantic-search list
```

### Index Information

Get details about a specific index:

```bash
semantic-search info my_project
```

### Delete Index

```bash
semantic-search delete my_project
```

## Example Output

### v0.2 - Chunk-based Search (Current)

```bash
# 1. Index project
$ semantic-search index ~/projects/my-django-app --name django_app
Loading embedding model: all-MiniLM-L6-v2
Model loaded. Embedding dimension: 384
Indexing directory: /Users/user/projects/my-django-app
Found 45 Python files
Found 234 code chunks
Creating embeddings for 234 chunks...
Created FAISS index with 234 vectors
✓ Successfully created index 'django_app'

# 2. Search (preview is enabled by default in v0.2)
$ semantic-search search "user authentication" --index django_app

Searching for: 'user authentication'
Index: django_app

Found 5 results:

  [1] function: authenticate_user
      Location: app/auth/views.py:42
      Score: 0.3421
      Signature: def authenticate_user(username: str, password: str) -> Optional[User]:
      Doc: Authenticate a user by username and password.

  [2] class: User
      Location: app/users/models.py:15
      Score: 0.4156
      Signature: class User(AbstractUser):
      Doc: Custom user model with additional fields.

  [3] method: AuthMiddleware.process_request
      Location: app/middleware/auth.py:28
      Score: 0.4892
      Signature: def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
      Doc: Process authentication for incoming requests.

  [4] class: UserSerializer
      Location: app/auth/serializers.py:10
      Score: 0.5234
      Signature: class UserSerializer(ModelSerializer):
      Doc: Serializer for User model authentication.

  [5] function: test_user_login
      Location: app/auth/tests.py:55
      Score: 0.6012
      Signature: def test_user_login() -> None:
```

## How It's Better Than grep

### 1. Understands Concepts and Synonyms

**Query:** "verify user identity"
- **grep:** Needs exact words: `grep -l "authentication\|login\|password"`
- **Semantic:** Understands concept "verify identity" = "authentication" ✓

### 2. Search Without Technical Terms

**Query:** "find unusual values in my data"
- **grep:** Need to know terms: `grep "outlier\|IQR\|quartile"`
- **Semantic:** Understands "unusual values" = "outliers detection" ✓

### 3. Natural Language Queries

**Query:** "teach computer to recognize patterns"
- **grep:** Has no idea this is ML: `grep "teach.*computer"` → 0 results
- **Semantic:** Understands it's ML → finds ml_model.py ✓

### 4. Relevance Ranking

Results are ranked by semantic similarity score:
- 0.0-1.0 = Highly relevant
- 1.0-1.5 = Relevant
- 1.5-2.0 = Moderately relevant
- \>2.0 = Less relevant

## Project Structure

```
semantic-search/
├── src/
│   └── semantic_search/      # Main package
│       ├── __init__.py       # Exports
│       ├── cli.py            # CLI interface
│       ├── embeddings.py     # Embedding models
│       ├── indexer.py        # File indexing
│       ├── searcher.py       # Search functionality
│       └── storage.py        # Index storage
├── .indexes/                 # Local indexes (git ignored)
├── CHANGELOG.md              # Change history
├── LICENSE                   # MIT license
├── README.md                 # This file
├── pyproject.toml            # Project configuration
└── requirements.txt          # Dependencies
```

## Where Are Indexes Stored?

Indexes are stored locally in:

```
~/.semantic_search/indexes/{index_name}/
├── index.faiss       # FAISS vector index
└── metadata.json     # Metadata (file paths, timestamps)
```

## Supported File Types

### v0.2 (current version):
- Python (.py) with chunk-based parsing
  - Functions, classes, and methods indexed separately
  - Signatures and docstrings extracted
  - Type hints preserved

### Future versions:
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
- Java (.java)
- Markdown (.md, .rst)

## Limitations in v0.3

- Python files only
- CLI only (Python API in v0.5)
- Basic AST parsing (no decorators, no nested functions)
- No Django/FastAPI specific features yet (coming in v0.4)

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed development plan.

### Current version:

- **v0.3** ✅ - Incremental updates
  - Update only changed files (10x faster)
  - SHA256 hash and mtime tracking
  - `update` CLI command
  - `--auto-update` flag for search
  - Smart file change detection

### Previous versions:

- **v0.2** ✅ - Chunk-based parsing (functions/classes/methods)
  - AST-based Python parser
  - Signature and docstring extraction
  - File:line location tracking
  - Preview mode with `--preview` flag

### Upcoming versions:

- **v0.4** - Django/FastAPI specific features
- **v0.5** - Python API
- **v0.6** - MCP integration for AI tools (Claude Code, Cursor)
- **v0.7** - Support for other languages
- **v0.8** - Hybrid search + filters
- **v1.0** - Production ready

### Setup for Development

```bash
# Clone repository
git clone https://github.com/steliarix/semantic-search.git
cd semantic-search

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Code Quality

```bash
# Format code
black src/

# Linting
ruff check src/

# Type checking (optional)
mypy src/
```

## FAQ

### How does it work?

1. **Indexing**: Read Python files → create embeddings → store in FAISS
2. **Search**: Create query embedding → find nearest vectors → return results

### Why FAISS?

FAISS is a fast library from Meta for vector similarity search, optimized for CPU/GPU.

### Why sentence-transformers?

Free pre-trained models that work locally without API keys.

### How much storage does an index use?

Depends on number of files. Approximately 1-5 MB per 100 files.

## License

MIT - see [LICENSE](LICENSE) for details.

## Author

Artem

## Support

- 📖 [Documentation](https://github.com/steliarix/semantic-search#readme)
- 🐛 [Report a bug](https://github.com/steliarix/semantic-search/issues)
- 💡 [Request a feature](https://github.com/steliarix/semantic-search/issues)
- 💬 [Discussions](https://github.com/steliarix/semantic-search/discussions)

## Acknowledgments

- [sentence-transformers](https://www.sbert.net/) for excellent embedding models
- [FAISS](https://github.com/facebookresearch/faiss) for fast vector search
- [Click](https://click.palletsprojects.com/) for convenient CLI framework
