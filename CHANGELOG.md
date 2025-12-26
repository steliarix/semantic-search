# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Django/FastAPI specific features - v0.4
- Python API for programmatic use - v0.5
- MCP integration for AI tools - v0.6

## [0.3.0] - 2025-12-27

### Added - Incremental Updates ⚡
- **Incremental index updating** - Only re-index changed files:
  - SHA256 hash tracking for file change detection
  - File modification timestamp (mtime) tracking
  - Automatic detection of new, changed, and deleted files
  - Preserves embeddings of unchanged files for efficiency
- **New CLI command `update`**:
  - `semantic-search update <index_name>` - Update existing index incrementally
  - Smart analysis: shows counts of new/changed/deleted/unchanged files
  - Skips update if no changes detected
- **Auto-update feature for search**:
  - `--auto-update` flag for `search` command
  - Automatically updates index before searching
  - Example: `semantic-search search "query" --index my_project --auto-update`
- **Enhanced metadata tracking**:
  - `file_metadata` dict with hash, mtime, and size for each file (chunk-based indexes)
  - `hash` and `mtime` fields added to file records (whole-file indexes)
  - `updated_at` timestamp to track last index update

### Improved
- **Indexing efficiency**:
  - Update only changed files instead of re-indexing entire project
  - Reuse existing embeddings for unchanged files
  - Faster updates for large codebases
- **FAISS index reconstruction**:
  - Smart rebuilding with kept + new embeddings
  - Maintains index consistency across updates
  - Supports both chunk-based and whole-file indexes

### Technical
- SHA256 hashing with `hashlib` for content verification
- File stat tracking with `Path.stat().st_mtime`
- Embedding reconstruction using `faiss.Index.reconstruct_n()`
- Numpy array operations for combining old and new embeddings
- Backward compatible with v0.1 and v0.2 indexes

### Example Usage
```bash
# Create initial index
semantic-search index ~/projects/my-app --name my_app

# Make some code changes...

# Update index incrementally (only changed files)
semantic-search update my_app

# Or auto-update before search
semantic-search search "user auth" --index my_app --auto-update
```

### Performance
- 10x faster updates for projects with few changes
- Typical update with 1-2 changed files: ~1-2 seconds
- Full re-index of same project: ~10-20 seconds

### Breaking Changes
- None - fully backward compatible with v0.1 and v0.2

## [0.2.0] - 2025-12-27

### Added - Chunk-based Parsing 🔍
- **AST-based Python parser** for extracting code chunks:
  - Functions with signatures and docstrings
  - Classes with inheritance information
  - Methods with parent class context
  - Automatic signature extraction with type hints
  - Docstring extraction for better semantic search
- **New parsers module** (`semantic_search.parsers/`):
  - `base_parser.py` - Abstract base class and `CodeChunk` dataclass
  - `python_parser.py` - Python AST parser implementation
- **Enhanced search results**:
  - Chunk type display (function, class, method)
  - File location with line numbers (`file.py:123`)
  - Parent class context for methods (`ClassName.method_name`)
  - Similarity scores for relevance ranking
- **Preview mode enabled by default** for search command:
  - Shows function/method signatures automatically
  - Displays first line of docstrings
  - Better code discovery experience
  - Use `--no-preview` to disable if needed

### Improved
- **Metadata structure**:
  - Stores chunk information (type, name, lines, signature, docstring, parent)
  - Maintains backward compatibility with v0.1 indexes
  - Added `use_chunking` flag to distinguish index versions
  - Stores `num_chunks` alongside `num_files`
- **CLI enhancements**:
  - `list` command shows chunk count for v0.2 indexes
  - `info` command displays chunk statistics
  - `search` command with improved formatting for chunk-based results
  - Color-coded output for better readability
- **SearchResult dataclass**:
  - Extended with chunk-specific fields
  - Backward compatible with v0.1 whole-file results
  - Smart `__str__` method for different index versions

### Technical
- AST (Abstract Syntax Tree) parsing for accurate code extraction
- Chunk-based indexing with 66 chunks from 9 test files
- Dual-mode indexing: chunk-based (v0.2) and whole-file (v0.1)
- Automatic format detection based on metadata
- No breaking changes - v0.1 indexes continue to work

### Example Output
```
[1] function: authenticate_user
    Location: auth.py:64
    Score: 0.8823
    Signature: def authenticate_user(username: str, password: str) -> Optional[User]:
    Doc: Authenticate a user by username and password.
```

### Breaking Changes
- None - fully backward compatible with v0.1

## [0.1.1] - 2025-12-26

### Improved
- Enhanced error handling in `storage.py`:
  - Added validation for missing `metadata.json` file
  - Added JSON parse error handling with descriptive messages
  - Added validation for required metadata fields
  - Added default values for missing metadata fields
- Enhanced search reliability in `searcher.py`:
  - Added empty query validation
  - Added `top_k` parameter validation (must be > 0)
  - Added empty index check to prevent errors
  - Auto-adjust `top_k` if it exceeds available vectors
  - Added handling for invalid FAISS indices (negative values)
- Enhanced CLI validation in `cli.py`:
  - Added empty search query validation at CLI level
  - Improved error messages for better user experience

### Fixed
- Fixed potential crash when searching with `top_k` larger than index size
- Fixed potential crash when loading corrupted metadata files
- Fixed edge case with empty search queries

### Technical
- Added comprehensive error handling throughout the codebase
- Improved input validation for all user-facing commands
- Better error messages for debugging

## [0.1.0] - 2025-12-26

### Added
- Basic indexing for Python files
- Embedding creation via sentence-transformers (all-MiniLM-L6-v2)
- Local FAISS index storage
- Semantic code search
- CLI interface with commands:
  - `index` - index a project directory
  - `search` - search within an index
  - `list` - list all available indexes
  - `info` - show detailed information about an index
  - `delete` - delete an index
- Automatic ignoring of service directories (.git, venv, __pycache__)
- Metadata storage in JSON format
- Python 3.9+ support

### Technical
- src-layout project structure
- pyproject.toml for modern Python packaging
- FAISS for vector similarity search
- sentence-transformers for embeddings
- Click for CLI framework
- Comprehensive testing on sample Python codebase

### Features Demonstrated
- Semantic understanding of code concepts
- Natural language queries support
- Synonym and concept recognition
- Relevance-based result ranking
- Superior to grep for conceptual searches

---

[unreleased]: https://github.com/steliarix/semantic-search/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/steliarix/semantic-search/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/steliarix/semantic-search/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/steliarix/semantic-search/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/steliarix/semantic-search/releases/tag/v0.1.0
