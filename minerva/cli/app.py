"""Minerva CLI application using Typer."""

import asyncio
from pathlib import Path
from typing import Annotated
from uuid import UUID

import sqlalchemy
import typer
from rich.console import Console
from rich.panel import Panel

from minerva import __version__
from minerva.config import settings
from minerva.core.ingestion.kindle_automation import KindleAutomation
from minerva.core.ingestion.pipeline import IngestionPipeline
from minerva.db.session import AsyncSessionLocal, engine
from minerva.utils.session_manager import ServiceType, SessionManager

app = typer.Typer(
    name="minerva",
    help="Minerva - Kindle Cloud Reader ingestion for research workflows",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Display version and exit."""
    if value:
        console.print(f"[bold cyan]Minerva[/bold cyan] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Minerva - Kindle Cloud Reader ingestion for research workflows."""
    pass


def validate_environment() -> None:
    """
    Validate required environment configuration.

    Raises:
        typer.Exit: If validation fails
    """
    errors = []

    # Check OPENAI_API_KEY
    if not settings.openai_api_key.get_secret_value():
        errors.append("OPENAI_API_KEY not set")

    # Check DATABASE_URL
    if not settings.database_url:
        errors.append("DATABASE_URL not set")

    # Check screenshots directory
    screenshots_dir = Path(settings.screenshots_dir)
    if not screenshots_dir.exists():
        try:
            screenshots_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create screenshots directory: {e}")
    elif not screenshots_dir.is_dir():
        errors.append(f"Screenshots path is not a directory: {screenshots_dir}")

    if errors:
        console.print("\n[bold red]❌ Configuration Errors:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        console.print(
            "\n[yellow]💡 Hint:[/yellow] Check your .env file or environment variables"
        )
        raise typer.Exit(code=1)


async def validate_database_connectivity() -> None:
    """
    Validate database connectivity.

    Raises:
        typer.Exit: If database connection fails
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
    except Exception as e:
        console.print("\n[bold red]❌ Database Connection Failed:[/bold red]")
        console.print(f"  {e}")
        console.print(
            "\n[yellow]💡 Hint:[/yellow] Verify DATABASE_URL and ensure PostgreSQL is running"
        )
        raise typer.Exit(code=1) from None


def validate_kindle_url(url: str) -> None:
    """
    Validate Kindle URL format.

    Args:
        url: Kindle Cloud Reader URL

    Raises:
        typer.Exit: If URL is invalid
    """
    if not url.startswith("https://read.amazon.com"):
        console.print(
            "\n[bold red]❌ Invalid Kindle URL:[/bold red]",
        )
        console.print("  Expected: https://read.amazon.com/...")
        console.print(f"  Got: {url}")
        raise typer.Exit(code=1)


@app.command()
def ingest(
    kindle_url: Annotated[
        str,
        typer.Argument(
            help="Kindle Cloud Reader book URL (https://read.amazon.com/...)"
        ),
    ],
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Book title (optional)"),
    ] = None,
    author: Annotated[
        str | None,
        typer.Option("--author", "-a", help="Book author (optional)"),
    ] = None,
    max_pages: Annotated[
        int,
        typer.Option("--max-pages", "-n", help="Maximum number of pages to capture (default: 1000)"),
    ] = 1000,
    rewind_presses: Annotated[
        int,
        typer.Option("--rewind-presses", help="Number of backward presses to reach book start (default: 100)"),
    ] = 100,
    page_delay_min: Annotated[
        float,
        typer.Option("--page-delay-min", help="Minimum delay in seconds between page turns (default: 5.0)"),
    ] = 5.0,
    page_delay_max: Annotated[
        float,
        typer.Option("--page-delay-max", help="Maximum delay in seconds between page turns (default: 10.0)"),
    ] = 10.0,
    use_ai_formatting: Annotated[
        bool,
        typer.Option("--use-ai-formatting", help="Use GPT-4o-mini to clean OCR output (adds ~$0.01/100 pages)"),
    ] = False,
    screenshots_only: Annotated[
        bool,
        typer.Option("--screenshots-only", help="Only capture screenshots, skip OCR and embeddings"),
    ] = False,
    force_auth: Annotated[
        bool,
        typer.Option("--force-auth", help="Force new authentication (ignore saved session)"),
    ] = False,
) -> None:
    """
    Ingest a Kindle book by capturing page screenshots.

    This command will:
    1. Validate environment and database connectivity
    2. Launch browser and navigate to Kindle URL (authenticate if needed)
    3. Capture pages up to max-pages limit (default: 1000)
    4. Save screenshots to disk
    5. Store metadata in database

    Examples:
        # Capture entire book (up to 1000 pages)
        minerva ingest "https://read.amazon.com/..." --title "My Book" --author "Author Name"

        # Capture only 40 pages for testing
        minerva ingest "https://read.amazon.com/..." --max-pages 40

        # Capture with forced authentication
        minerva ingest "https://read.amazon.com/..." --force-auth --max-pages 50
    """
    # Validate environment
    validate_environment()
    validate_kindle_url(kindle_url)

    # Welcome message
    console.print(
        Panel.fit(
            "[bold cyan]Minerva[/bold cyan] - Kindle Ingestion Pipeline\n"
            f"Version {__version__}",
            border_style="cyan",
        )
    )

    # Configuration summary
    console.print("\n[bold]Configuration:[/bold]")
    console.print(f"  Embedding Model: {settings.embedding_model}")
    console.print(f"  Database: {settings.database_url.split('@')[-1]}")
    console.print(f"  Screenshots: {settings.screenshots_dir}")

    # Clear session if force_auth is requested
    if force_auth:
        console.print("\n[yellow]🔄 Force authentication requested - clearing saved session...[/yellow]")
        session_manager = SessionManager()
        if session_manager.clear_session(ServiceType.KINDLE):
            console.print("[green]✓ Session cleared[/green]")
        else:
            console.print("[dim]No existing session to clear[/dim]")

    try:

        async def run_ingestion() -> UUID:
            # Validate database connectivity
            console.print("\n[bold]Validating database connectivity...[/bold]")
            try:
                await validate_database_connectivity()
                console.print("  ✓ Database connection successful")
            except typer.Exit:
                raise

            # Start ingestion
            console.print("\n[bold]Starting ingestion:[/bold]")
            console.print(f"  URL: {kindle_url}")
            if title:
                console.print(f"  Title: {title}")
            if author:
                console.print(f"  Author: {author}")
            console.print(f"  Max Pages: {max_pages}")
            console.print()

            kindle = KindleAutomation(headless=False)
            await kindle.launch(use_saved_session=not force_auth)

            try:
                book_id = await kindle.capture_full_book(
                    kindle_url=kindle_url,
                    book_title=title,
                    book_author=author,
                    max_pages=max_pages,
                    rewind_presses=rewind_presses,
                    page_delay_min=page_delay_min,
                    page_delay_max=page_delay_max,
                )

                # If screenshots_only flag is set, stop here
                if screenshots_only:
                    console.print("\n[yellow]⏸️  Screenshots-only mode: Skipping OCR and embeddings[/yellow]")
                    return book_id

                # Otherwise, continue with full pipeline
                console.print("\n[bold cyan]📝 Starting OCR extraction and processing...[/bold cyan]\n")
                if use_ai_formatting:
                    console.print("[dim]AI formatting enabled (GPT-4o-mini cleanup)[/dim]\n")

                # Run the pipeline (OCR → Chunking → Embeddings)
                async with AsyncSessionLocal() as session:
                    pipeline = IngestionPipeline(
                        session=session,
                        use_ai_formatting=use_ai_formatting,
                    )
                    await pipeline.process_existing_book(book_id=book_id)

                console.print("\n[bold green]✅ Full pipeline complete![/bold green]")
                return book_id
            finally:
                await kindle.close()

        book_id = asyncio.run(run_ingestion())

        # Success message (different for screenshots-only vs full pipeline)
        if screenshots_only:
            next_steps = (
                "Next steps:\n"
                "  • Run OCR extraction: minerva process <book-id>\n"
                "  • Or run full pipeline on next ingestion (without --screenshots-only)"
            )
        else:
            next_steps = (
                "✅ All processing complete!\n"
                "  • OCR extraction: Done\n"
                "  • Semantic chunking: Done\n"
                "  • Vector embeddings: Done\n\n"
                "Ready to use:\n"
                "  • Start API: uvicorn minerva.main:app --reload\n"
                "  • Search UI: http://localhost:8000/search-ui\n"
                "  • API docs: http://localhost:8000/docs"
            )

        console.print(
            Panel.fit(
                f"[bold green]✅ Ingestion Complete![/bold green]\n\n"
                f"Book ID: {book_id}\n"
                f"Screenshots: {settings.screenshots_dir}/{book_id}\n\n"
                f"{next_steps}",
                title="Success",
                border_style="green",
            )
        )

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠️  Ingestion cancelled by user (Ctrl+C)[/yellow]")
        raise typer.Exit(code=130) from None

    except Exception as e:
        console.print("\n[bold red]❌ Ingestion Failed:[/bold red]")
        console.print(f"  {type(e).__name__}: {e}")
        console.print(
            "\n[yellow]💡 Hint:[/yellow] Check logs for more details or retry"
        )
        raise typer.Exit(code=1) from None


@app.command()
def export(
    book_id: Annotated[
        UUID | None,
        typer.Argument(help="UUID of book to export (omit to use --all flag)"),
    ] = None,
    all_books: Annotated[
        bool, typer.Option("--all", help="Export all completed books")
    ] = False,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Output directory for SQL files"),
    ] = Path("exports"),
) -> None:
    """
    Export book(s) to production-ready SQL file.

    Generates SQL file with INSERT statements for book, chunks with embeddings,
    and screenshot metadata (excluding file paths). Use generated SQL file to
    import into production database.

    Examples:
      minerva export 123e4567-e89b-12d3-a456-426614174000
      minerva export --all
      minerva export 123e4567-e89b-12d3-a456-426614174000 --output-dir /tmp/exports
    """
    from rich.table import Table

    from minerva.core.export.export_service import (
        export_all_books,
        generate_sql_export,
        validate_and_report,
    )
    from minerva.db.session import AsyncSessionLocal

    # Validate arguments
    if not all_books and book_id is None:
        console.print(
            "[bold red]Error:[/bold red] Must provide either book_id or --all flag"
        )
        raise typer.Exit(code=1)

    if all_books and book_id is not None:
        console.print(
            "[bold yellow]Warning:[/bold yellow] Ignoring book_id when --all is specified"
        )

    console.print(
        Panel.fit(
            "[bold cyan]Minerva Export Tool[/bold cyan]\n\n"
            "Generate production-ready SQL export files",
            border_style="cyan",
        )
    )

    async def run_export() -> None:
        """Run export process."""
        async with AsyncSessionLocal() as session:
            if all_books:
                # Batch export all completed books
                console.print(
                    "\n[bold]Exporting all completed books...[/bold]\n",
                    style="cyan",
                )

                export_paths = await export_all_books(session, output_dir)

                if export_paths:
                    console.print(
                        f"\n[bold green]✅ Exported {len(export_paths)} book(s)![/bold green]\n"
                    )
                    console.print(f"📁 Export directory: {output_dir.absolute()}\n")

                    # List exported files
                    table = Table(title="Exported Files")
                    table.add_column("File", style="cyan")
                    table.add_column("Size", justify="right")

                    for path in export_paths:
                        size_mb = path.stat().st_size / (1024 * 1024)
                        table.add_row(path.name, f"{size_mb:.2f} MB")

                    console.print(table)
                else:
                    console.print(
                        "[yellow]No completed books found to export[/yellow]"
                    )

            else:
                # Single book export
                assert book_id is not None  # Type narrowing

                # Validate and get report
                console.print("[bold]Validating book...[/bold]", style="cyan")

                try:
                    report = await validate_and_report(book_id, session)
                except ValueError as e:
                    console.print(f"\n[bold red]❌ Validation Failed:[/bold red] {e}")
                    raise typer.Exit(code=1) from e

                # Display report
                console.print("\n[bold cyan]Export Report[/bold cyan]\n")

                table = Table(show_header=False)
                table.add_row("Book Title", report.title)
                table.add_row("Author", report.author or "Unknown")
                table.add_row("Total Chunks", str(report.total_chunks))
                table.add_row("Total Screenshots", str(report.total_screenshots))
                table.add_row(
                    "Estimated Size", f"{report.estimated_size_mb} MB"
                )

                console.print(table)

                # Show warnings
                if report.warnings:
                    console.print("\n[bold yellow]Warnings:[/bold yellow]")
                    for warning in report.warnings:
                        console.print(f"  ⚠️  {warning}")

                # Confirm export
                console.print(
                    f"\nExport '{report.title}' to production SQL file? [y/n]: ",
                    end="",
                )
                response = input().strip().lower()

                if response != "y":
                    console.print("\n[yellow]Export cancelled[/yellow]")
                    raise typer.Exit(code=0)

                # Generate export
                console.print("\n[bold]Generating SQL export...[/bold]", style="cyan")
                export_path = await generate_sql_export(book_id, session, output_dir)

                # Success message
                console.print("\n[bold green]✅ Export Complete![/bold green]\n")
                console.print(f"📄 Export File: {export_path.absolute()}")

                size_mb = export_path.stat().st_size / (1024 * 1024)
                console.print(f"📦 Size: {size_mb:.2f} MB")
                console.print(f"📚 Book: {report.title}")
                console.print(f"📝 Chunks: {report.total_chunks}\n")

                console.print("[bold cyan]Import Instructions:[/bold cyan]")
                console.print(f"  1. Copy {export_path.name} to production server")
                console.print(
                    f"  2. Run: psql $PRODUCTION_DATABASE_URL -f {export_path.name}"
                )
                console.print(
                    f"  3. Verify: SELECT COUNT(*) FROM chunks WHERE book_id = '{book_id}';"
                )
                console.print()

    try:
        asyncio.run(run_export())

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠️  Export cancelled by user (Ctrl+C)[/yellow]")
        raise typer.Exit(code=130) from None

    except Exception as e:
        console.print("\n[bold red]❌ Export Failed:[/bold red]")
        console.print(f"  {type(e).__name__}: {e}")
        raise typer.Exit(code=1) from None


@app.command()
def process(
    book_id: Annotated[
        UUID,
        typer.Argument(help="UUID of book to process"),
    ],
) -> None:
    """
    Process existing book screenshots (OCR → Chunking → Embeddings).

    Use this command to:
    - Resume failed ingestions
    - Process books captured with --screenshots-only
    - Re-process books with different settings

    Examples:
        minerva process a21d7330-ffe2-40f3-b970-1a4c5a812d21
    """
    console.print(
        Panel.fit(
            "[bold cyan]Minerva[/bold cyan] - Book Processing Pipeline\n"
            f"Version {__version__}",
            border_style="cyan",
        )
    )

    console.print(f"\n[bold]Processing book:[/bold] {book_id}\n")

    try:

        async def run_processing() -> None:
            async with AsyncSessionLocal() as session:
                pipeline = IngestionPipeline(session=session)
                book = await pipeline.process_existing_book(book_id=book_id)

                console.print(
                    Panel.fit(
                        f"[bold green]✅ Processing Complete![/bold green]\n\n"
                        f"Book: {book.title}\n"
                        f"Author: {book.author}\n"
                        f"Status: {book.ingestion_status}\n\n"
                        f"The book is now ready for semantic search!",
                        title="Success",
                        border_style="green",
                    )
                )

        asyncio.run(run_processing())

    except ValueError as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {e}")
        console.print("\n[yellow]💡 Hint:[/yellow] Check the book ID is correct")
        raise typer.Exit(code=1) from None

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠️  Processing cancelled by user (Ctrl+C)[/yellow]")
        raise typer.Exit(code=130) from None

    except Exception as e:
        console.print("\n[bold red]❌ Processing Failed:[/bold red]")
        console.print(f"  {type(e).__name__}: {e}")
        console.print(
            "\n[yellow]💡 Hint:[/yellow] Check logs for more details or retry"
        )
        raise typer.Exit(code=1) from None


@app.command()
def session(
    action: Annotated[
        str,
        typer.Argument(
            help="Action to perform: 'status', 'clear <service>', or 'clear --all'"
        ),
    ],
    service: Annotated[
        str | None,
        typer.Argument(help="Service name (e.g., 'kindle') for clear action"),
    ] = None,
    all_sessions: Annotated[
        bool,
        typer.Option("--all", help="Clear all sessions"),
    ] = False,
) -> None:
    """
    Manage authentication sessions for data sources.

    Actions:
      status              Show status of all sessions
      status <service>    Show status of specific service session
      clear <service>     Clear session for specific service
      clear --all         Clear all sessions

    Examples:
      minerva session status
      minerva session status kindle
      minerva session clear kindle
      minerva session clear --all
    """
    from rich.table import Table

    session_manager = SessionManager()

    # Handle 'status' action
    if action == "status":
        console.print("\n[bold]Session Status:[/bold]\n")

        if service:
            # Show specific service status
            try:
                service_type = ServiceType(service.lower())
                info = session_manager.get_session_info(service_type)

                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("Service")
                table.add_column("Status")
                table.add_column("Path")
                table.add_column("Modified")

                status = "✓ Active" if info.exists else "✗ No session"
                modified = (
                    info.modified_at.strftime("%Y-%m-%d %H:%M:%S")
                    if info.modified_at
                    else "-"
                )

                table.add_row(
                    service_type.value,
                    f"[green]{status}[/green]" if info.exists else f"[dim]{status}[/dim]",
                    str(info.path),
                    modified,
                )

                console.print(table)

            except ValueError:
                console.print(f"[red]❌ Unknown service: {service}[/red]")
                console.print(f"Available services: {', '.join(s.value for s in ServiceType)}")
                raise typer.Exit(code=1)

        else:
            # Show all sessions
            sessions = session_manager.list_sessions()

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Service")
            table.add_column("Status")
            table.add_column("Size")
            table.add_column("Modified")

            for info in sessions:
                status = "✓ Active" if info.exists else "✗ No session"
                size = f"{info.size_bytes} bytes" if info.size_bytes else "-"
                modified = (
                    info.modified_at.strftime("%Y-%m-%d %H:%M:%S")
                    if info.modified_at
                    else "-"
                )

                table.add_row(
                    info.service.value,
                    f"[green]{status}[/green]" if info.exists else f"[dim]{status}[/dim]",
                    size,
                    modified,
                )

            console.print(table)
            console.print(f"\nSession directory: {session_manager.sessions_dir}")

    # Handle 'clear' action
    elif action == "clear":
        if all_sessions:
            # Clear all sessions
            console.print("\n[yellow]⚠️  Clearing all sessions...[/yellow]\n")

            results = session_manager.clear_all_sessions()
            cleared = [s.value for s, cleared in results.items() if cleared]

            if cleared:
                console.print(f"[green]✓ Cleared sessions:[/green] {', '.join(cleared)}")
            else:
                console.print("[dim]No sessions to clear[/dim]")

        elif service:
            # Clear specific service session
            try:
                service_type = ServiceType(service.lower())

                console.print(f"\n[yellow]⚠️  Clearing {service_type.value} session...[/yellow]\n")

                if session_manager.clear_session(service_type):
                    console.print(f"[green]✓ {service_type.value} session cleared[/green]")
                    console.print(f"\nNext login will require authentication")
                else:
                    console.print(f"[dim]No {service_type.value} session found[/dim]")

            except ValueError:
                console.print(f"[red]❌ Unknown service: {service}[/red]")
                console.print(f"Available services: {', '.join(s.value for s in ServiceType)}")
                raise typer.Exit(code=1)

        else:
            console.print("[red]❌ Please specify a service or use --all[/red]")
            console.print("Example: minerva session clear kindle")
            console.print("         minerva session clear --all")
            raise typer.Exit(code=1)

    else:
        console.print(f"[red]❌ Unknown action: {action}[/red]")
        console.print("Valid actions: status, clear")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
