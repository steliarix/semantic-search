"""
CLI interface for semantic search.

Provides command-line commands for indexing and searching.
"""

import click
from semantic_search.indexer import Indexer
from semantic_search.searcher import Searcher
from semantic_search.storage import IndexStorage


@click.group()
@click.version_option(version="0.3.0")
def cli():
    """
    Semantic Search - Local semantic search for Python projects.

    A free, local, and privacy-focused semantic search tool.
    """
    pass


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--name', '-n', required=True, help='Name for the index')
@click.option('--model', '-m', default=None, help='Embedding model to use (default: all-MiniLM-L6-v2)')
def index(directory, name, model):
    """
    Index a directory of Python files.

    DIRECTORY: Path to the directory to index

    Example:
        semantic-search index /path/to/project --name my_project
    """
    try:
        indexer = Indexer()
        if model:
            from semantic_search.embeddings import EmbeddingModel
            indexer.embedding_model = EmbeddingModel(model_name=model)

        indexer.index_directory(directory, name)
        click.echo(click.style(f"\n✓ Successfully created index '{name}'", fg='green'))

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        raise click.Abort()


@cli.command()
@click.argument('index_name')
def update(index_name):
    """
    Update an existing index incrementally.

    Only re-indexes files that have changed, adds new files,
    and removes deleted files from the index.

    INDEX_NAME: Name of the index to update

    Example:
        semantic-search update my_project
    """
    try:
        indexer = Indexer()
        indexer.update_index(index_name)
        click.echo(click.style(f"\n✓ Successfully updated index '{index_name}'", fg='green'))

    except FileNotFoundError as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        click.echo("Use 'semantic-search list' to see available indexes")
        raise click.Abort()

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        raise click.Abort()


@cli.command()
@click.argument('query')
@click.option('--index', '-i', required=True, help='Name of the index to search')
@click.option('--top-k', '-k', default=5, help='Number of results to return (default: 5)')
@click.option('--preview/--no-preview', '-p', default=True, help='Show code preview for results (default: enabled)')
@click.option('--auto-update/--no-auto-update', default=False, help='Automatically update index before searching (default: disabled)')
def search(query, index, top_k, preview, auto_update):
    """
    Search for code semantically similar to the query.

    QUERY: Search query text

    Examples:
        semantic-search search "user authentication" --index my_project
        semantic-search search "database models" --index my_project --no-preview
        semantic-search search "API endpoints" --index my_project --auto-update
    """
    try:
        # Validate query
        if not query or not query.strip():
            click.echo(click.style("\n✗ Error: Search query cannot be empty", fg='red'), err=True)
            raise click.Abort()

        # Auto-update if requested
        if auto_update:
            click.echo("Checking for index updates...")
            try:
                indexer = Indexer()
                indexer.update_index(index, show_progress=False)
                click.echo()
            except Exception as e:
                click.echo(click.style(f"Warning: Auto-update failed: {e}", fg='yellow'))
                click.echo("Continuing with existing index...\n")

        searcher = Searcher(index_name=index)

        click.echo(f"\nSearching for: '{query}'")
        click.echo(f"Index: {index}\n")

        results = searcher.search(query, top_k=top_k)

        if not results:
            click.echo(click.style("No results found", fg='yellow'))
            return

        click.echo(click.style(f"Found {len(results)} results:\n", fg='green'))

        for result in results:
            # Show chunk-based results with better formatting
            if result.chunk_type:
                location = f"{result.file_path}:{result.start_line}"
                if result.parent:
                    context = f"{result.parent}.{result.name}"
                else:
                    context = result.name

                click.echo(f"  [{result.rank}] {click.style(result.chunk_type, fg='yellow')}: {click.style(context, fg='cyan')}")
                click.echo(f"      Location: {click.style(location, fg='blue')}")
                click.echo(f"      Score: {result.score:.4f}")

                if preview:
                    if result.signature:
                        click.echo(f"      Signature: {click.style(result.signature, fg='green')}")
                    if result.docstring:
                        first_line = result.docstring.split('\n')[0].strip()
                        click.echo(f"      Doc: {first_line}")
            else:
                # v0.1 whole-file results
                click.echo(f"  [{result.rank}] {click.style(result.file_path, fg='cyan')}")
                click.echo(f"      Score: {result.score:.4f}")

            click.echo()

    except FileNotFoundError as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        click.echo("Use 'semantic-search list' to see available indexes")
        raise click.Abort()

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        raise click.Abort()


@cli.command()
def list():
    """
    List all available indexes.

    Example:
        semantic-search list
    """
    try:
        storage = IndexStorage()
        indexes = storage.list_indexes()

        if not indexes:
            click.echo(click.style("No indexes found", fg='yellow'))
            click.echo("\nCreate an index with: semantic-search index <directory> --name <name>")
            return

        click.echo(click.style(f"Available indexes ({len(indexes)}):\n", fg='green'))

        for index_name in indexes:
            try:
                info = storage.get_index_info(index_name)
                click.echo(f"  • {click.style(index_name, fg='cyan')}")
                click.echo(f"    Path: {info['indexed_path']}")
                click.echo(f"    Files: {info['num_files']}")

                # Show chunks info for v0.2+ indexes
                if 'num_chunks' in info:
                    click.echo(f"    Chunks: {info['num_chunks']}")

                click.echo(f"    Created: {info['created_at']}")
                click.echo()
            except Exception as e:
                click.echo(f"  • {index_name} (error loading info: {e})")

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        raise click.Abort()


@cli.command()
@click.argument('index_name')
def info(index_name):
    """
    Show detailed information about an index.

    INDEX_NAME: Name of the index

    Example:
        semantic-search info my_project
    """
    try:
        storage = IndexStorage()
        info = storage.get_index_info(index_name)

        click.echo(click.style(f"\nIndex: {index_name}\n", fg='green'))
        click.echo(f"  Indexed path: {info['indexed_path']}")
        click.echo(f"  Created at: {info['created_at']}")
        click.echo(f"  Number of files: {info['num_files']}")

        # Show chunks info for v0.2+ indexes
        if 'num_chunks' in info:
            click.echo(f"  Number of chunks: {info['num_chunks']}")

        click.echo(f"  Number of vectors: {info['num_vectors']}")
        click.echo(f"  Embedding dimension: {info['dimension']}")
        click.echo()

    except FileNotFoundError as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        raise click.Abort()

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        raise click.Abort()


@cli.command()
@click.argument('index_name')
@click.confirmation_option(prompt='Are you sure you want to delete this index?')
def delete(index_name):
    """
    Delete an index.

    INDEX_NAME: Name of the index to delete

    Example:
        semantic-search delete my_project
    """
    try:
        storage = IndexStorage()
        storage.delete_index(index_name)
        click.echo(click.style(f"\n✓ Deleted index '{index_name}'", fg='green'))

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red'), err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()
