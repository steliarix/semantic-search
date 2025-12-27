# Python API

## CodeSense Class

Main API class for programmatic access.

### Constructor

```python
from codesense import CodeSense

cs = CodeSense(
    index_name="my_project",
    embedding_model=None,  # Optional: model name
    storage_path=None      # Optional: custom storage path
)
```

**Parameters:**

- `index_name` (str) - Index identifier
- `embedding_model` (str, optional) - Embedding model name (default: all-MiniLM-L6-v2)
- `storage_path` (str, optional) - Custom index storage path

**Alias:**

```python
from codesense import SemanticSearch  # Same as CodeSense
```

---

### Methods

#### index()

Index a directory.

```python
cs.index(
    directory="/path/to/project",
    show_progress=True,      # Show progress bar
    use_chunking=True        # Chunk-based parsing (recommended)
)
```

**Parameters:**

- `directory` (str) - Path to index
- `show_progress` (bool) - Show progress bar
- `use_chunking` (bool) - Use chunk-based parsing

**Raises:**

- `FileNotFoundError` - Directory not found
- `ValueError` - Invalid directory

---

#### search()

Search for code.

```python
results = cs.search(
    query="user authentication",
    top_k=5,                # Number of results
    filter_type=None,       # Filter by type
    auto_update=False       # Update before search
)
```

**Parameters:**

- `query` (str) - Search query
- `top_k` (int) - Number of results (default: 5)
- `filter_type` (str, optional) - Filter: model, route, view, django, fastapi, flask
- `auto_update` (bool) - Update index before search

**Returns:**

- `List[SearchResult]` - Search results

**Raises:**

- `FileNotFoundError` - Index not found
- `ValueError` - Empty query or invalid top_k

---

#### update()

Update index incrementally.

```python
cs.update(show_progress=True)
```

**Parameters:**

- `show_progress` (bool) - Show progress bar

**Raises:**

- `FileNotFoundError` - Index not found

---

#### info()

Get index information.

```python
info = cs.info()
```

**Returns:**

Dictionary with:
- `index_name` (str) - Index name
- `num_files` (int) - File count
- `num_chunks` (int) - Chunk count
- `num_vectors` (int) - Vector count
- `dimension` (int) - Embedding dimension
- `created_at` (str) - Creation timestamp
- `indexed_path` (str) - Indexed directory path

---

#### exists()

Check if index exists.

```python
if cs.exists():
    # Index exists
```

**Returns:**

- `bool` - True if exists

---

#### delete()

Delete the index.

```python
cs.delete()
```

**Raises:**

- `FileNotFoundError` - Index not found

---

### Static Methods

#### list_indexes()

List all indexes.

```python
indexes = CodeSense.list_indexes(storage_path=None)
```

**Returns:**

- `List[str]` - Index names

---

#### get_all_index_info()

Get info for all indexes.

```python
all_info = CodeSense.get_all_index_info(storage_path=None)
```

**Returns:**

- `Dict[str, Dict]` - Index name → info dict

---

## SearchResult Class

Search result attributes.

```python
result.rank           # int: Ranking (1, 2, 3, ...)
result.file_path      # str: Relative file path
result.score          # float: Similarity score (lower = better)

# Chunk-specific (if chunk-based indexing):
result.chunk_type     # str: function, class, method
result.name           # str: Function/class name
result.start_line     # int: Start line number
result.end_line       # int: End line number
result.signature      # str: Function/class signature
result.docstring      # str: Docstring content
result.parent         # str: Parent class (for methods)

# Framework-specific:
result.framework_type # str: django_model, fastapi_route, etc.
result.http_method    # str: GET, POST, etc.
result.route_path     # str: /api/users
```

---

## Basic Usage

```python
from codesense import CodeSense

# Initialize
cs = CodeSense(index_name="myapp")

# Index directory
cs.index("/path/to/project")

# Search
results = cs.search("authentication", top_k=5)
for result in results:
    print(f"{result.file_path}:{result.start_line}")
    print(f"  {result.signature}")

# Update
cs.update()

# Get info
info = cs.info()
print(f"Files: {info['num_files']}")
```

## Advanced Usage

### Custom Model

```python
cs = CodeSense(
    index_name="myapp",
    embedding_model="all-mpnet-base-v2"  # More accurate, slower
)
```

### Filter Results

```python
# By framework type
results = cs.search("product", filter_type="model")

# By score threshold
high_quality = [r for r in results if r.score < 1.0]

# By framework
fastapi_only = [r for r in results if r.framework_type == "fastapi_route"]
```

### Group by File

```python
from collections import defaultdict

results = cs.search("user", top_k=20)
by_file = defaultdict(list)

for result in results:
    by_file[result.file_path].append(result)

for file_path, file_results in by_file.items():
    print(f"{file_path}: {len(file_results)} matches")
```

### Error Handling

```python
try:
    cs = CodeSense(index_name="myapp")
    if not cs.exists():
        cs.index("/path/to/project")

    results = cs.search("query")

except FileNotFoundError as e:
    print(f"Index not found: {e}")

except ValueError as e:
    print(f"Invalid input: {e}")
```

---

See [examples.md](examples.md) for more examples.
