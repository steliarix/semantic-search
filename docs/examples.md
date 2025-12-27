# Examples

## CLI Examples

### Basic Indexing and Search

```bash
# Index a Django project
codesense index ~/projects/ecommerce --name shop

# Find authentication code
codesense search "user login authentication" --index shop

# Find models
codesense search "product model" --index shop
```

### Framework-Specific Search

```bash
# Django models only
codesense search "user model" --index shop --filter django

# FastAPI routes only
codesense search "api endpoint" --index shop --filter fastapi

# All routes (FastAPI + Flask)
codesense search "product endpoint" --index shop --filter route
```

### Natural Language Queries

```bash
# Auto-detects "model" intent
codesense search "product model" --index shop

# Auto-detects "route" intent
codesense search "api endpoint for orders" --index shop

# Auto-detects "django" framework
codesense search "django serializer" --index shop
```

### Incremental Updates

```bash
# Initial index
codesense index ~/project --name proj

# ... make code changes ...

# Update only changed files
codesense update proj

# Or auto-update before search
codesense search "query" --index proj --auto-update
```

### Multiple Indexes

```bash
# Create multiple project indexes
codesense index ~/backend --name backend
codesense index ~/frontend --name frontend
codesense index ~/shared --name shared

# List all indexes
codesense list

# Search specific project
codesense search "authentication" --index backend
```

---

## Python API Examples

### Basic Usage

```python
from codesense import CodeSense

# Initialize and index
cs = CodeSense(index_name="myapp")
cs.index("~/projects/myapp")

# Search
results = cs.search("user authentication", top_k=5)
for result in results:
    print(f"[{result.rank}] {result.file_path}:{result.start_line}")
    if result.signature:
        print(f"  {result.signature}")
    print()
```

### Integration in CI/CD

```python
import os
from codesense import CodeSense

# Index codebase for documentation
cs = CodeSense(index_name="docs_index")

if not cs.exists():
    cs.index(os.getcwd())
else:
    cs.update()

# Find all API endpoints
endpoints = cs.search("api endpoint route", top_k=50, filter_type="route")

# Generate API documentation
for ep in endpoints:
    if ep.http_method and ep.route_path:
        print(f"{ep.http_method} {ep.route_path}")
        print(f"  Handler: {ep.name}")
        if ep.docstring:
            print(f"  {ep.docstring.split(chr(10))[0]}")
```

### Code Analysis Tool

```python
from codesense import CodeSense
from collections import Counter

cs = CodeSense(index_name="analysis")
cs.index("/path/to/project")

# Find all database models
models = cs.search("model", top_k=100, filter_type="model")

# Analyze by framework
frameworks = Counter(m.framework_type for m in models)
print("Models by framework:")
for fw, count in frameworks.items():
    print(f"  {fw}: {count}")

# Find authentication code
auth_code = cs.search("authentication login", top_k=20)
print(f"\nFound {len(auth_code)} authentication-related code chunks")
```

### Pre-commit Hook

```python
#!/usr/bin/env python3
"""Pre-commit hook: Update code index"""

from codesense import CodeSense
import sys

try:
    cs = CodeSense(index_name="project")

    if cs.exists():
        cs.update(show_progress=False)
        print("✓ Code index updated")
    else:
        print("⚠ Code index not found. Run: codesense index . --name project")

except Exception as e:
    print(f"⚠ Index update failed: {e}")
    # Don't block commit
    sys.exit(0)
```

### Filter and Group Results

```python
from codesense import CodeSense
from collections import defaultdict

cs = CodeSense(index_name="myapp")
results = cs.search("user", top_k=30)

# Filter by score
high_quality = [r for r in results if r.score < 1.0]
print(f"High quality results: {len(high_quality)}")

# Filter by type
models = [r for r in results if "model" in (r.framework_type or "")]
views = [r for r in results if "view" in (r.framework_type or "")]

# Group by file
by_file = defaultdict(list)
for result in results:
    by_file[result.file_path].append(result)

print("\nResults by file:")
for file_path in sorted(by_file.keys()):
    print(f"  {file_path}: {len(by_file[file_path])} matches")
```

### Multi-Project Search

```python
from codesense import CodeSense

# Search across multiple projects
projects = ["backend", "frontend", "api", "shared"]
query = "authentication"

all_results = []
for proj in projects:
    try:
        cs = CodeSense(index_name=proj)
        results = cs.search(query, top_k=10)
        all_results.extend([(proj, r) for r in results])
    except FileNotFoundError:
        print(f"⚠ Index '{proj}' not found")

# Sort by score
all_results.sort(key=lambda x: x[1].score)

# Display
for proj, result in all_results[:20]:
    print(f"[{proj}] {result.file_path}:{result.start_line}")
    print(f"  Score: {result.score:.4f}")
```

### Custom Embedding Model

```python
from codesense import CodeSense

# Use more accurate model (slower, better quality)
cs = CodeSense(
    index_name="research",
    embedding_model="all-mpnet-base-v2"
)

cs.index("/path/to/project")
results = cs.search("complex algorithm", top_k=5)
```

### Batch Processing

```python
from codesense import CodeSense
import os

# Index all projects in a directory
projects_dir = "~/workspace"

for project_name in os.listdir(projects_dir):
    project_path = os.path.join(projects_dir, project_name)

    if not os.path.isdir(project_path):
        continue

    print(f"Indexing {project_name}...")

    cs = CodeSense(index_name=project_name)
    try:
        cs.index(project_path, show_progress=False)
        print(f"  ✓ Indexed: {cs.info()['num_files']} files")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
```

### Index Management

```python
from codesense import CodeSense
import datetime

# List all indexes with details
all_info = CodeSense.get_all_index_info()

for name, info in all_info.items():
    created = info['created_at']
    print(f"{name}:")
    print(f"  Files: {info['num_files']}")
    print(f"  Chunks: {info.get('num_chunks', 'N/A')}")
    print(f"  Path: {info['indexed_path']}")
    print(f"  Created: {created}")

    # Delete old indexes (older than 30 days)
    created_date = datetime.datetime.fromisoformat(created)
    age = datetime.datetime.now() - created_date

    if age.days > 30:
        cs = CodeSense(index_name=name)
        cs.delete()
        print(f"  ✓ Deleted (age: {age.days} days)")
```

---

## Real-World Use Cases

### 1. Code Exploration

When joining a new project, quickly find relevant code:

```bash
codesense search "database connection setup" --index newproject
codesense search "user authentication flow" --index newproject
codesense search "payment processing" --index newproject
```

### 2. Refactoring

Find all code that needs updating:

```bash
# Find deprecated patterns
codesense search "old authentication method" --index proj

# Find specific library usage
codesense search "requests library http call" --index proj
```

### 3. Security Audit

Find security-sensitive code:

```bash
codesense search "password hashing" --index proj
codesense search "sql query" --index proj
codesense search "file upload" --index proj
```

### 4. Documentation Generation

```python
# Find all API endpoints
cs = CodeSense(index_name="api")
endpoints = cs.search("endpoint route", top_k=100, filter_type="route")

# Generate OpenAPI spec
for ep in endpoints:
    print(f"  {ep.http_method} {ep.route_path}")
```

### 5. Code Review

```python
# Find complex functions
cs = CodeSense(index_name="review")
results = cs.search("function", top_k=50)

# Analyze
for r in results:
    if r.chunk_type == "function":
        lines = r.end_line - r.start_line
        if lines > 50:
            print(f"⚠ Long function: {r.name} ({lines} lines)")
```

---

See also:
- [CLI Usage](cli-usage.md)
- [Python API](python-api.md)
