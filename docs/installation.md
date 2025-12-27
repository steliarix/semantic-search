# Installation

## From PyPI

```bash
pip install codesense
```

## From Source

```bash
git clone https://github.com/steliarix/codesense.git
cd codesense
pip install -e .
```

For development with optional dependencies:

```bash
pip install -e ".[dev]"
```

## Requirements

- **Python**: 3.9 or higher
- **RAM**: 1GB minimum (for embedding model)
- **Storage**: ~1-5 MB per 100 indexed files
- **Internet**: Required for initial model download (~80MB), then works offline

## Dependencies

Installed automatically:

- `sentence-transformers>=2.0.0` - Embedding model
- `faiss-cpu>=1.7.0` - Vector search
- `click>=8.0.0` - CLI framework
- `tqdm>=4.65.0` - Progress bars
- `numpy>=1.21.0` - Array operations
- `torch>=2.0.0` - ML backend

## Verify Installation

```bash
# Check version
codesense --version

# List available commands
codesense --help
```

## First-Time Setup

The embedding model downloads automatically on first use (~80MB).

```bash
# This triggers model download
codesense index ~/test-project --name test

# Model is cached at:
# ~/.cache/torch/sentence_transformers/
```

## Troubleshooting

### Import Error

```bash
# Ensure codesense is in Python path
python -c "import codesense; print(codesense.__version__)"
```

### Command Not Found

```bash
# Add to PATH (if installed with --user)
export PATH="$HOME/.local/bin:$PATH"
```

### GPU Support (Optional)

For faster indexing with GPU:

```bash
pip uninstall faiss-cpu
pip install faiss-gpu
```

Requires CUDA-compatible GPU.
