# CLI Usage

## Commands

### index

Index a directory of Python files.

```bash
codesense index <directory> --name <index_name>
```

**Options:**

- `--name`, `-n` (required) - Name for the index
- `--model`, `-m` (optional) - Embedding model (default: all-MiniLM-L6-v2)

**Example:**

```bash
codesense index ~/projects/django-app --name myapp
codesense index /path/to/project --name proj --model all-mpnet-base-v2
```

Auto-detects Django, FastAPI, Flask frameworks.

---

### search

Search for code semantically.

```bash
codesense search <query> --index <index_name>
```

**Options:**

- `--index`, `-i` (required) - Index to search
- `--top-k`, `-k` (optional) - Number of results (default: 5)
- `--filter`, `-f` (optional) - Filter by type (model, route, view, django, fastapi, flask)
- `--auto-update` (optional) - Update index before searching
- `--no-preview` (optional) - Disable code preview

**Examples:**

```bash
# Basic search
codesense search "user authentication" --index myapp

# More results
codesense search "database" --index myapp --top-k 10

# Filter by type
codesense search "product" --index myapp --filter model

# Auto-update before search
codesense search "api" --index myapp --auto-update
```

**Smart Intent Detection:**

Query keywords auto-filter results:

- "product **model**" → finds only models
- "**api endpoint**" → finds only routes
- "**django** user" → finds only Django code
- "**fastapi** route" → finds only FastAPI routes

---

### update

Update index incrementally (only changed files).

```bash
codesense update <index_name>
```

**Example:**

```bash
codesense update myapp
```

10x faster than full re-index.

---

### list

List all indexes.

```bash
codesense list
```

Shows: index name, file count, chunk count, creation date.

---

### info

Show detailed index information.

```bash
codesense info <index_name>
```

**Example:**

```bash
codesense info myapp
```

Shows: indexed path, file count, chunk count, vectors, embedding model.

---

### delete

Delete an index.

```bash
codesense delete <index_name>
```

Requires confirmation prompt.

---

## Global Options

```bash
codesense --version  # Show version
codesense --help     # Show help
```

## Output Format

Search results show:

```
[1] fastapi_route: get_user
    Location: api/routes.py:42
    Score: 0.8234
    Route: GET /users/{user_id}
    Signature: async def get_user(user_id: int):
    Doc: Get user by ID.
```

**Score:** Lower = more similar (0.0-1.0 highly relevant)

## Index Storage

Indexes stored at: `~/.codesense/indexes/<index_name>/`

Contents:
- `index.faiss` - Vector index
- `metadata.json` - File metadata

## Common Workflows

**Initial setup:**

```bash
codesense index ~/project --name proj
codesense search "authentication" --index proj
```

**After code changes:**

```bash
codesense update proj
```

**Find specific patterns:**

```bash
codesense search "pydantic model" --index proj
codesense search "django view" --index proj --filter view
```
