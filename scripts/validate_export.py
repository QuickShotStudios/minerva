#!/usr/bin/env python3
"""Validate SQL export files before production import."""

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def validate_export_file(export_path: Path) -> tuple[bool, list[str]]:
    """
    Validate SQL export file for production import.

    Checks:
    - No file_path values (screenshots excluded)
    - Transaction wrapper present (BEGIN/COMMIT)
    - Required tables included
    - ON CONFLICT clauses for idempotency

    Args:
        export_path: Path to SQL export file

    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings: list[str] = []
    is_valid = True

    if not export_path.exists():
        return False, [f"❌ File not found: {export_path}"]

    with open(export_path, encoding="utf-8") as f:
        sql_content = f.read()

    # Check for non-NULL file paths (security risk)
    if "file_path" in sql_content:
        # Check each line with file_path
        for line in sql_content.split("\n"):
            if "file_path" in line.lower() and "null" not in line.lower():
                # If it's in an INSERT statement and not NULL, that's a problem
                if "insert into screenshots" in sql_content.lower():
                    warnings.append(
                        "❌ SECURITY: file_path contains non-NULL values in screenshots"
                    )
                    is_valid = False
                    break

    # Check for transaction wrapper
    if "BEGIN;" not in sql_content:
        warnings.append("⚠️  Missing BEGIN transaction statement")
        is_valid = False

    if "COMMIT;" not in sql_content:
        warnings.append("⚠️  Missing COMMIT transaction statement")
        is_valid = False

    # Check for required tables
    required_tables = ["books", "chunks", "screenshots", "embedding_configs"]
    missing_tables = []
    for table in required_tables:
        if f"INSERT INTO {table}" not in sql_content.lower():
            missing_tables.append(table)

    if missing_tables:
        warnings.append(
            f"⚠️  Missing INSERT statements for: {', '.join(missing_tables)}"
        )

    # Check for ON CONFLICT (idempotency)
    if "ON CONFLICT" not in sql_content:
        warnings.append("⚠️  Missing ON CONFLICT clauses (import not idempotent)")

    # Check for embeddings
    if "embedding" not in sql_content.lower():
        warnings.append("❌ No embeddings found in export")
        is_valid = False

    # Check file size
    file_size_mb = export_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 500:
        warnings.append(f"⚠️  Large export file: {file_size_mb:.1f} MB")

    # Count chunks (approximate)
    chunk_inserts = sql_content.lower().count("insert into chunks")
    if chunk_inserts == 0:
        warnings.append("❌ No chunk records found")
        is_valid = False
    elif chunk_inserts > 1000:
        warnings.append(f"ℹ️  Large number of chunks: ~{chunk_inserts}")

    return is_valid, warnings


def main() -> int:
    """Main entry point for validation script."""
    console.print(
        "\n[bold cyan]Minerva Export Validator[/bold cyan]\n",
        "Validates SQL export files before production import\n",
    )

    if len(sys.argv) < 2:
        console.print("[bold red]Error:[/bold red] Missing export file path")
        console.print("\nUsage: python scripts/validate_export.py <export_file.sql>")
        console.print(
            "\nExample: python scripts/validate_export.py exports/book_123_20251007.sql"
        )
        return 1

    export_path = Path(sys.argv[1])

    console.print(f"📄 Validating: [cyan]{export_path}[/cyan]\n")

    # Run validation
    is_valid, warnings = validate_export_file(export_path)

    # Display results
    if is_valid and not warnings:
        console.print("[bold green]✅ Export file is valid![/bold green]\n")
        console.print("Safe to import to production database.\n")
        return 0

    # Show warnings/errors
    if warnings:
        table = Table(title="Validation Results", show_header=False)
        table.add_column("Issue", style="yellow")

        for warning in warnings:
            if "❌" in warning:
                table.add_row(warning, style="bold red")
            elif "⚠️" in warning:
                table.add_row(warning, style="yellow")
            else:
                table.add_row(warning, style="cyan")

        console.print(table)
        console.print()

    if not is_valid:
        console.print(
            "[bold red]❌ Export file FAILED validation[/bold red]\n"
        )
        console.print("Do NOT import this file to production.\n")
        return 1

    console.print(
        "[bold yellow]⚠️  Export file has warnings but is importable[/bold yellow]\n"
    )
    console.print("Review warnings before importing to production.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
