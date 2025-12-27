# CodeSense

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI-powered semantic code search for Python projects. Auto-detects Django, FastAPI, Flask and understands natural language queries.

## Key Features

- **Smart Search** - Natural language queries with auto-intent detection
- **Framework Support** - Auto-detects Django, FastAPI, Flask patterns
- **Python API** - Use programmatically in your code
- **Fast & Local** - FAISS-powered search, all data stored locally
- **Incremental Updates** - Update only changed files, 10x faster
- **Chunk-based** - Search functions, classes, methods separately

## Installation

```bash
pip install codesense
```

From source:
```bash
git clone https://github.com/steliarix/codesense.git
cd codesense
pip install -e .
```

See [Installation Guide](docs/installation.md) for details.

## Quick Start

### CLI

```bash
# Index your project
codesense index ~/projects/my-app --name my_app

# Search with natural language
codesense search "user authentication" --index my_app

# Update after code changes
codesense update my_app
```

### Python API

```python
from codesense import CodeSense

cs = CodeSense(index_name="my_project")
cs.index("/path/to/project")

results = cs.search("user authentication", top_k=5)
for result in results:
    print(f"{result.file_path}:{result.start_line}")
```

## Documentation

- [Installation](docs/installation.md) - Installation methods and setup
- [CLI Usage](docs/cli-usage.md) - Command reference and options
- [Python API](docs/python-api.md) - API reference and methods
- [Examples](docs/examples.md) - Real-world usage examples

## How It Works

1. **Index** - Parse Python files using AST, extract code chunks
2. **Embed** - Create semantic embeddings with sentence-transformers
3. **Search** - Find similar code using FAISS vector similarity

CodeSense understands concepts, not just keywords:
- "verify user identity" → finds authentication code
- "product model" → finds only Django/Pydantic models
- "api endpoint" → finds FastAPI/Flask routes

## Technologies

- [sentence-transformers](https://www.sbert.net/) - Semantic embeddings
- [FAISS](https://github.com/facebookresearch/faiss) - Vector search
- [Click](https://click.palletsprojects.com/) - CLI framework

## Roadmap

- ✅ v0.4 - Universal framework support + Python API
- ✅ v0.3 - Incremental updates
- ✅ v0.2 - Chunk-based parsing
- 🔜 v0.6 - MCP integration for AI tools
- 🔜 v0.7 - Multi-language support (JS, TypeScript, Java)

See [CHANGELOG.md](CHANGELOG.md) for full version history.

## Requirements

- Python 3.9+
- 1GB RAM (for embedding model)
- ~1-5 MB storage per 100 indexed files

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [GitHub](https://github.com/steliarix/codesense)
- [Issues](https://github.com/steliarix/codesense/issues)
- [PyPI](https://pypi.org/project/codesense/)

---

**Author**: Artem | **Version**: 0.4.0
