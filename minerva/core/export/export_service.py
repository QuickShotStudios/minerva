"""Export service for generating production-ready SQL export files."""

import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.db.models.book import Book
from minerva.db.models.chunk import Chunk
from minerva.db.models.embedding_config import EmbeddingConfig
from minerva.db.models.screenshot import Screenshot

logger = structlog.get_logger(__name__)


class ExportReport:
    """Pre-export validation report."""

    def __init__(
        self,
        book_id: UUID,
        title: str,
        author: str | None,
        total_chunks: int,
        total_screenshots: int,
        estimated_size_mb: float,
        warnings: list[str],
    ):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.total_chunks = total_chunks
        self.total_screenshots = total_screenshots
        self.estimated_size_mb = estimated_size_mb
        self.warnings = warnings


async def validate_and_report(
    book_id: UUID, session: AsyncSession
) -> ExportReport:
    """
    Validate book is ready for export and generate pre-export report.

    Args:
        book_id: UUID of book to validate
        session: Database session

    Returns:
        ExportReport with validation results and size estimates

    Raises:
        ValueError: If book not found, not completed, or missing embeddings
    """
    logger.info("validating_book_for_export", book_id=str(book_id))

    # Fetch book
    book = await session.get(Book, book_id)
    if not book:
        raise ValueError(f"Book {book_id} not found")

    # Check ingestion status
    if book.ingestion_status != "completed":
        raise ValueError(
            f"Book not ready for export. Status: {book.ingestion_status}. "
            "Only completed books can be exported."
        )

    # Fetch all chunks and validate embeddings
    chunks_query = select(Chunk).where(Chunk.book_id == book_id)
    chunks_result = await session.execute(chunks_query)
    chunks = list(chunks_result.scalars().all())

    if not chunks:
        raise ValueError("Book has no chunks. Cannot export empty book.")

    # Check for missing embeddings
    missing_embeddings = [c.id for c in chunks if c.embedding is None]
    if missing_embeddings:
        raise ValueError(
            f"{len(missing_embeddings)} chunk(s) missing embeddings. "
            "All chunks must have embeddings before export."
        )

    # Calculate export size estimate
    total_text_size = sum(len(c.chunk_text.encode("utf-8")) for c in chunks)
    embedding_size = len(chunks) * 1536 * 4  # 1536 floats, 4 bytes each
    total_size_mb = (total_text_size + embedding_size) / (1024 * 1024)

    # Collect warnings
    warnings: list[str] = []
    if total_size_mb > 100:
        warnings.append(f"Large export ({total_size_mb:.1f}MB > 100MB)")
    if len(chunks) > 500:
        warnings.append(f"Many chunks ({len(chunks)} > 500)")

    logger.info(
        "validation_complete",
        book_id=str(book_id),
        total_chunks=len(chunks),
        size_mb=round(total_size_mb, 2),
        warnings_count=len(warnings),
    )

    return ExportReport(
        book_id=book_id,
        title=book.title,
        author=book.author,
        total_chunks=len(chunks),
        total_screenshots=book.total_screenshots or 0,
        estimated_size_mb=round(total_size_mb, 2),
        warnings=warnings,
    )


async def generate_sql_export(
    book_id: UUID, session: AsyncSession, output_dir: Path
) -> Path:
    """
    Generate SQL export file for book with all related data.

    Generates INSERT statements for:
    - Embedding configuration (with ON CONFLICT)
    - Book record (excluding local paths)
    - Screenshot metadata (file_path set to NULL)
    - Text chunks with embeddings

    Args:
        book_id: UUID of book to export
        session: Database session
        output_dir: Directory to save export file

    Returns:
        Path to generated SQL file

    Raises:
        ValueError: If book or required data not found
    """
    logger.info("generating_sql_export", book_id=str(book_id))

    # Fetch all required data
    book = await session.get(Book, book_id)
    if not book:
        raise ValueError(f"Book {book_id} not found")

    chunks_query = select(Chunk).where(Chunk.book_id == book_id).order_by(Chunk.chunk_sequence)
    chunks_result = await session.execute(chunks_query)
    chunks = list(chunks_result.scalars().all())

    screenshots_query = (
        select(Screenshot)
        .where(Screenshot.book_id == book_id)
        .order_by(Screenshot.sequence_number)
    )
    screenshots_result = await session.execute(screenshots_query)
    screenshots = list(screenshots_result.scalars().all())

    # Get embedding config from first chunk
    embedding_config = None
    if chunks and chunks[0].embedding_config_id:
        embedding_config = await session.get(EmbeddingConfig, chunks[0].embedding_config_id)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{book_id}_{timestamp}.sql"
    output_path = output_dir / filename

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write SQL file
    with open(output_path, "w", encoding="utf-8") as f:
        # Header with metadata
        f.write("-- ============================================\n")
        f.write("-- Minerva Knowledge Base Export\n")
        f.write("-- ============================================\n")
        f.write(f"-- Book: {book.title}\n")
        if book.author:
            f.write(f"-- Author: {book.author}\n")
        f.write(f"-- Book ID: {book_id}\n")
        f.write(f"-- Exported: {datetime.now().isoformat()}\n")
        f.write(f"-- Total Chunks: {len(chunks)}\n")
        f.write(f"-- Total Screenshots: {len(screenshots)}\n")
        f.write("--\n")
        f.write("-- IMPORTANT: Screenshot file_path fields are NULL\n")
        f.write("-- Screenshots are NOT included in this export\n")
        f.write("-- ============================================\n\n")

        # Transaction wrapper
        f.write("BEGIN;\n\n")

        # Embedding configuration (idempotent with ON CONFLICT)
        if embedding_config:
            f.write("-- Embedding Configuration\n")
            f.write(
                "INSERT INTO embedding_configs (id, model_name, model_version, dimensions, is_active, created_at)\n"
            )
            f.write(
                f"VALUES ('{embedding_config.id}', '{embedding_config.model_name}', "
            )
            f.write(
                f"'{embedding_config.model_version or 'v1'}', {embedding_config.dimensions}, "
            )
            f.write(
                f"{str(embedding_config.is_active).lower()}, '{embedding_config.created_at.isoformat()}')\n"
            )
            f.write("ON CONFLICT (id) DO NOTHING;\n\n")

        # Book record (exclude local paths, use ON CONFLICT for idempotency)
        f.write("-- Book Record\n")
        f.write(
            "INSERT INTO books (id, title, author, kindle_url, total_screenshots, "
            "capture_date, ingestion_status, metadata, created_at, updated_at)\n"
        )

        # Escape single quotes in text fields
        title_escaped = book.title.replace("'", "''")
        author_escaped = book.author.replace("'", "''") if book.author else None
        author_value = f"'{author_escaped}'" if author_escaped else "NULL"
        metadata_json = json.dumps(book.metadata).replace("'", "''") if book.metadata else None
        metadata_value = f"'{metadata_json}'" if metadata_json else "NULL"
        screenshots_value = book.total_screenshots if book.total_screenshots else "NULL"

        f.write(f"VALUES ('{book.id}', '{title_escaped}', ")
        f.write(f"{author_value}, ")
        f.write(f"'{book.kindle_url}', {screenshots_value}, ")
        f.write(f"'{book.capture_date.isoformat()}', 'completed', ")
        f.write(f"{metadata_value}, ")
        f.write(f"'{book.created_at.isoformat()}', '{book.updated_at.isoformat()}')\n")
        f.write("ON CONFLICT (id) DO UPDATE SET updated_at = EXCLUDED.updated_at;\n\n")

        # Screenshots metadata (file_path explicitly NULL for production)
        if screenshots:
            f.write(
                "-- Screenshot Metadata (file_path NULL - screenshots NOT exported)\n"
            )
            for screenshot in screenshots:
                f.write(
                    "INSERT INTO screenshots (id, book_id, sequence_number, file_path, "
                    "screenshot_hash, captured_at)\n"
                )
                f.write(
                    f"VALUES ('{screenshot.id}', '{screenshot.book_id}', "
                    f"{screenshot.sequence_number}, NULL, '{screenshot.screenshot_hash}', "
                    f"'{screenshot.captured_at.isoformat()}')\n"
                )
                f.write("ON CONFLICT (id) DO NOTHING;\n")
            f.write("\n")

        # Text chunks with embeddings
        f.write(f"-- Text Chunks with Embeddings ({len(chunks)} chunks)\n")
        for i, chunk in enumerate(chunks, 1):
            # Convert embedding to PostgreSQL vector format
            embedding_array = "{" + ",".join(map(str, chunk.embedding)) + "}"

            # Convert screenshot_ids UUID array to PostgreSQL array format
            screenshot_ids_str = (
                "ARRAY["
                + ",".join(f"'{sid}'" for sid in chunk.screenshot_ids)
                + "]::uuid[]"
                if chunk.screenshot_ids
                else "ARRAY[]::uuid[]"
            )

            # Escape chunk text
            chunk_text_escaped = chunk.chunk_text.replace("'", "''")

            f.write(
                "INSERT INTO chunks (id, book_id, screenshot_ids, chunk_sequence, "
                "chunk_text, chunk_token_count, embedding_config_id, embedding, "
                "vision_model, created_at)\n"
            )
            f.write(
                f"VALUES ('{chunk.id}', '{chunk.book_id}', {screenshot_ids_str}, "
            )
            f.write(
                f"{chunk.chunk_sequence}, '{chunk_text_escaped}', {chunk.chunk_token_count}, "
            )
            f.write(
                f"'{chunk.embedding_config_id}', '{embedding_array}'::vector, "
            )
            f.write(f"'{chunk.vision_model}', '{chunk.created_at.isoformat()}')\n")
            f.write("ON CONFLICT (id) DO NOTHING;\n")

            # Add progress comment every 50 chunks
            if i % 50 == 0:
                f.write(f"-- Progress: {i}/{len(chunks)} chunks\n")

        # Commit transaction
        f.write("\nCOMMIT;\n")
        f.write("\n-- Export complete\n")

    logger.info(
        "sql_export_complete",
        book_id=str(book_id),
        output_path=str(output_path),
        chunks_exported=len(chunks),
        screenshots_exported=len(screenshots),
    )

    return output_path


async def export_all_books(session: AsyncSession, output_dir: Path) -> list[Path]:
    """
    Export all completed books to SQL files.

    Args:
        session: Database session
        output_dir: Directory to save export files

    Returns:
        List of paths to generated SQL files
    """
    logger.info("exporting_all_books")

    # Find all completed books
    query = select(Book).where(Book.ingestion_status == "completed")
    result = await session.execute(query)
    books = list(result.scalars().all())

    logger.info("found_completed_books", count=len(books))

    exported_files: list[Path] = []
    failed_books: list[tuple[str, str]] = []

    for book in books:
        try:
            # Validate first
            await validate_and_report(book.id, session)

            # Generate export
            export_path = await generate_sql_export(book.id, session, output_dir)
            exported_files.append(export_path)

            logger.info("book_exported", book_id=str(book.id), title=book.title)

        except Exception as e:
            logger.error(
                "book_export_failed",
                book_id=str(book.id),
                title=book.title,
                error=str(e),
            )
            failed_books.append((book.title, str(e)))

    logger.info(
        "batch_export_complete",
        total_books=len(books),
        exported=len(exported_files),
        failed=len(failed_books),
    )

    return exported_files
