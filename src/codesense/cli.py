"""
CLI interface for codesense.

Provides command-line commands for indexing and searching code.
Organized using command groups for better maintainability.
"""

from typing import Any, Optional

import click

from codesense.tools.indexer import Indexer
from codesense.tools.searcher import Searcher, SearchResult
from codesense.util.storage import IndexStorage


class AutoRegisteringGroup(click.Group):
    """
    Base class for command groups that auto-registers commands.

    Automatically discovers and registers Click commands defined as
    static methods on subclasses.
    """

    def __init__(self, name: str, help: str):
        """Initialize the command group and auto-register commands."""
        super().__init__(name=name, help=help)
        for attr in dir(self.__class__):
            cmd = getattr(self.__class__, attr)
            if isinstance(cmd, click.Command):
                self.add_command(cmd)


class OutputFormatter:
    """Utility class for formatting CLI output with colors."""

    @staticmethod
    def success(message: str) -> None:
        """Print success message in green."""
        click.echo(click.style(f"\n✓ {message}", fg="green"))

    @staticmethod
    def error(message: str, hint: Optional[str] = None) -> None:
        """Print error message in red with optional hint."""
        click.echo(click.style(f"\n✗ Error: {message}", fg="red"), err=True)
        if hint:
            click.echo(hint)

    @staticmethod
    def warning(message: str) -> None:
        """Print warning message in yellow."""
        click.echo(click.style(message, fg="yellow"))

    @staticmethod
    def info(message: str) -> None:
        """Print info message."""
        click.echo(message)

    @staticmethod
    def format_result(result: SearchResult, preview: bool = True) -> None:
        """Format and display a single search result."""
        if result.chunk_type:
            OutputFormatter._format_chunk_result(result, preview)
        else:
            OutputFormatter._format_file_result(result)
        click.echo()

    @staticmethod
    def _format_chunk_result(result: SearchResult, preview: bool) -> None:
        """Format chunk-based search result."""
        location = f"{result.file_path}:{result.start_line}"
        context = (
            f"{result.parent}.{result.name}"
            if result.parent
            else result.name
        )

        display_type = (
            result.framework_type
            if result.framework_type
            else result.chunk_type
        )

        click.echo(
            f"  [{result.rank}] "
            f"{click.style(display_type, fg='yellow')}: "
            f"{click.style(context, fg='cyan')}"
        )
        click.echo(f"      Location: {click.style(location, fg='blue')}")
        click.echo(f"      Score: {result.score:.4f}")

        if preview:
            OutputFormatter._show_preview(result)

    @staticmethod
    def _format_file_result(result: SearchResult) -> None:
        """Format whole-file search result."""
        click.echo(
            f"  [{result.rank}] {click.style(result.file_path, fg='cyan')}"
        )
        click.echo(f"      Score: {result.score:.4f}")

    @staticmethod
    def _show_preview(result: SearchResult) -> None:
        """Show preview information for a result."""
        if result.http_method and result.route_path:
            click.echo(
                f"      Route: "
                f"{click.style(result.http_method, fg='magenta')} "
                f"{result.route_path}"
            )

        if result.signature:
            click.echo(
                f"      Signature: "
                f"{click.style(result.signature, fg='green')}"
            )

        if result.docstring:
            first_line = result.docstring.split("\n")[0].strip()
            click.echo(f"      Doc: {first_line}")


class IndexCommands(AutoRegisteringGroup):
    """Commands for managing code indexes."""

    def __init__(self):
        super().__init__(
            name="index-commands",
            help="Commands for creating and managing indexes",
        )

    @staticmethod
    @click.command()
    @click.argument("directory", type=click.Path(exists=True))
    @click.option("--name", "-n", required=True, help="Name for the index")
    @click.option(
        "--model",
        "-m",
        default=None,
        help="Embedding model (default: all-MiniLM-L6-v2)",
    )
    def index(directory: str, name: str, model: Optional[str]) -> None:
        """
        Index a directory of Python files.

        Automatically detects Django, FastAPI, Flask, and generic Python.

        Examples:
            codesense index /path/to/project --name my_project
            codesense index ~/django-app --name my_app
        """
        try:
            indexer = Indexer()
            if model:
                from codesense.util.embeddings import EmbeddingModel

                indexer.embedding_model = EmbeddingModel(model_name=model)

            indexer.index_directory(directory, name)
            OutputFormatter.success(f"Successfully created index '{name}'")

        except Exception as e:
            OutputFormatter.error(str(e))
            raise click.Abort() from e

    @staticmethod
    @click.command()
    @click.argument("index_name")
    def update(index_name: str) -> None:
        """
        Update an existing index incrementally.

        Only re-indexes changed files for faster updates.

        Example:
            codesense update my_project
        """
        try:
            indexer = Indexer()
            indexer.update_index(index_name)
            OutputFormatter.success(
                f"Successfully updated index '{index_name}'"
            )

        except FileNotFoundError as e:
            OutputFormatter.error(
                str(e), hint="Use 'codesense list' to see available indexes"
            )
            raise click.Abort() from e

        except Exception as e:
            OutputFormatter.error(str(e))
            raise click.Abort() from e

    @staticmethod
    @click.command()
    @click.argument("index_name")
    @click.confirmation_option(
        prompt="Are you sure you want to delete this index?"
    )
    def delete(index_name: str) -> None:
        """
        Delete an index.

        Example:
            codesense delete my_project
        """
        try:
            storage = IndexStorage()
            storage.delete_index(index_name)
            OutputFormatter.success(f"Deleted index '{index_name}'")

        except Exception as e:
            OutputFormatter.error(str(e))
            raise click.Abort() from e


class SearchCommands(AutoRegisteringGroup):
    """Commands for searching code."""

    def __init__(self):
        super().__init__(
            name="search-commands", help="Commands for searching code"
        )

    @staticmethod
    @click.command()
    @click.argument("query")
    @click.option(
        "--index", "-i", required=True, help="Name of the index to search"
    )
    @click.option(
        "--top-k", "-k", default=5, help="Number of results (default: 5)"
    )
    @click.option(
        "--preview/--no-preview",
        "-p",
        default=True,
        help="Show code preview (default: enabled)",
    )
    @click.option(
        "--auto-update/--no-auto-update",
        default=False,
        help="Auto-update index before search (default: disabled)",
    )
    @click.option(
        "--filter",
        "-f",
        "filter_type",
        default=None,
        help="Filter by type (model, route, view, django, fastapi, flask)",
    )
    def search(
        query: str,
        index: str,
        top_k: int,
        preview: bool,
        auto_update: bool,
        filter_type: Optional[str],
    ) -> None:
        """
        Search for code semantically similar to the query.

        Examples:
            codesense search "user authentication" --index my_project
            codesense search "database models" -i my_project --no-preview
            codesense search "API endpoints" -i my_app --auto-update
            codesense search "user model" -i my_app --filter model
        """
        try:
            SearchCommands._validate_query(query)
            SearchCommands._handle_auto_update(index, auto_update)

            searcher = Searcher(index_name=index)
            SearchCommands._display_search_info(query, filter_type, index)

            results = searcher.search(
                query, top_k=top_k, filter_type=filter_type
            )

            SearchCommands._display_results(results, preview)

        except FileNotFoundError as e:
            OutputFormatter.error(
                str(e), hint="Use 'codesense list' to see available indexes"
            )
            raise click.Abort() from e

        except Exception as e:
            OutputFormatter.error(str(e))
            raise click.Abort() from e

    @staticmethod
    def _validate_query(query: str) -> None:
        """Validate that query is not empty."""
        if not query or not query.strip():
            OutputFormatter.error("Search query cannot be empty")
            raise click.Abort()

    @staticmethod
    def _handle_auto_update(index: str, auto_update: bool) -> None:
        """Handle auto-update if requested."""
        if not auto_update:
            return

        OutputFormatter.info("Checking for index updates...")
        try:
            indexer = Indexer()
            indexer.update_index(index, show_progress=False)
            click.echo()
        except Exception as e:
            OutputFormatter.warning(f"Warning: Auto-update failed: {e}")
            OutputFormatter.info("Continuing with existing index...\n")

    @staticmethod
    def _display_search_info(
        query: str, filter_type: Optional[str], index: str
    ) -> None:
        """Display search query information."""
        click.echo(f"\nSearching for: '{query}'")
        if filter_type:
            click.echo(f"Filter: {filter_type}")
        click.echo(f"Index: {index}\n")

    @staticmethod
    def _display_results(
        results: list[SearchResult], preview: bool
    ) -> None:
        """Display search results."""
        if not results:
            OutputFormatter.warning("No results found")
            return

        click.echo(
            click.style(f"Found {len(results)} results:\n", fg="green")
        )

        for result in results:
            OutputFormatter.format_result(result, preview)


class InfoCommands(AutoRegisteringGroup):
    """Commands for viewing index information."""

    def __init__(self):
        super().__init__(
            name="info-commands", help="Commands for viewing index info"
        )

    @staticmethod
    @click.command(name="list")
    def list_indexes() -> None:
        """
        List all available indexes.

        Example:
            codesense list
        """
        try:
            storage = IndexStorage()
            indexes = storage.list_indexes()

            if not indexes:
                OutputFormatter.warning("No indexes found")
                OutputFormatter.info(
                    "\nCreate an index with: "
                    "codesense index <directory> --name <name>"
                )
                return

            click.echo(
                click.style(
                    f"Available indexes ({len(indexes)}):\n", fg="green"
                )
            )

            for index_name in indexes:
                InfoCommands._display_index_summary(storage, index_name)

        except Exception as e:
            OutputFormatter.error(str(e))
            raise click.Abort() from e

    @staticmethod
    def _display_index_summary(
        storage: IndexStorage, index_name: str
    ) -> None:
        """Display summary for a single index."""
        try:
            info = storage.get_index_info(index_name)
            click.echo(f"  • {click.style(index_name, fg='cyan')}")
            click.echo(f"    Path: {info['indexed_path']}")
            click.echo(f"    Files: {info['num_files']}")

            if "num_chunks" in info:
                click.echo(f"    Chunks: {info['num_chunks']}")

            click.echo(f"    Created: {info['created_at']}")
            click.echo()
        except Exception as e:
            click.echo(f"  • {index_name} (error loading info: {e})")

    @staticmethod
    @click.command()
    @click.argument("index_name")
    def info(index_name: str) -> None:
        """
        Show detailed information about an index.

        Example:
            codesense info my_project
        """
        try:
            storage = IndexStorage()
            info = storage.get_index_info(index_name)

            click.echo(click.style(f"\nIndex: {index_name}\n", fg="green"))
            InfoCommands._display_index_details(info)

        except FileNotFoundError as e:
            OutputFormatter.error(str(e))
            raise click.Abort() from e

        except Exception as e:
            OutputFormatter.error(str(e))
            raise click.Abort() from e

    @staticmethod
    def _display_index_details(info: dict[str, Any]) -> None:
        """Display detailed index information."""
        click.echo(f"  Indexed path: {info['indexed_path']}")
        click.echo(f"  Created at: {info['created_at']}")
        click.echo(f"  Number of files: {info['num_files']}")

        if "num_chunks" in info:
            click.echo(f"  Number of chunks: {info['num_chunks']}")

        click.echo(f"  Number of vectors: {info['num_vectors']}")
        click.echo(f"  Embedding dimension: {info['dimension']}")
        click.echo()


# Main CLI group
@click.group()
@click.version_option(version="0.4.0")
def cli() -> None:
    """
    CodeSense - AI-powered semantic code search.

    A free, local, and privacy-focused semantic search tool for Python.
    """


# Register command groups
index_commands = IndexCommands()
search_commands = SearchCommands()
info_commands = InfoCommands()

# Add commands to main CLI
cli.add_command(index_commands.commands["index"])
cli.add_command(index_commands.commands["update"])
cli.add_command(index_commands.commands["delete"])
cli.add_command(search_commands.commands["search"])
cli.add_command(info_commands.commands["list"])
cli.add_command(info_commands.commands["info"])


if __name__ == "__main__":
    cli()
