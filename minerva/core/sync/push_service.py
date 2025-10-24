"""Push service for sending books directly to production database."""

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from uuid import UUID

from minerva.config import settings
from minerva.core.export.export_service import validate_and_report, ExportReport
from minerva.db.models.book import Book
from minerva.db.models.chunk import Chunk
from minerva.db.models.embedding_config import EmbeddingConfig
from minerva.db.models.screenshot import Screenshot

logger = structlog.get_logger(__name__)


class SyncStatus:
    """Represents the sync status of books between local and production."""

    def __init__(
        self,
        book_id: UUID,
        title: str,
        author: str | None,
        status: str,  # "local_only", "production_only", "synced", "needs_update"
        local_chunks: int | None,
        production_chunks: int | None,
        local_status: str | None,
        production_status: str | None,
        local_updated: str | None,
        production_updated: str | None,
    ):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.status = status
        self.local_chunks = local_chunks
        self.production_chunks = production_chunks
        self.local_status = local_status
        self.production_status = production_status
        self.local_updated = local_updated
        self.production_updated = production_updated


class ProductionBook:
    """Represents a book found in production database."""

    def __init__(
        self,
        id: UUID,
        title: str,
        author: str | None,
        ingestion_status: str,
        total_chunks: int,
        created_at: str,
        updated_at: str,
    ):
        self.id = id
        self.title = title
        self.author = author
        self.ingestion_status = ingestion_status
        self.total_chunks = total_chunks
        self.created_at = created_at
        self.updated_at = updated_at


async def check_production_book_exists(book_id: UUID) -> ProductionBook | None:
    """
    Check if a book exists in production database.

    Args:
        book_id: UUID of book to check

    Returns:
        ProductionBook if found, None otherwise

    Raises:
        ValueError: If production database URL is not configured
    """
    if not settings.production_database_url:
        raise ValueError(
            "Production database URL not configured. "
            "Set PRODUCTION_DATABASE_URL in .env file."
        )

    logger.info("checking_production_book", book_id=str(book_id))

    # Create production database connection
    engine = create_async_engine(settings.production_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Query for book and chunk count
            query = text("""
                SELECT
                    b.id,
                    b.title,
                    b.author,
                    b.ingestion_status,
                    COUNT(c.id) as chunk_count,
                    b.created_at,
                    b.updated_at
                FROM books b
                LEFT JOIN chunks c ON c.book_id = b.id
                WHERE b.id = :book_id
                GROUP BY b.id, b.title, b.author, b.ingestion_status, b.created_at, b.updated_at
            """)

            result = await session.execute(query, {"book_id": str(book_id)})
            row = result.fetchone()

            if row:
                return ProductionBook(
                    id=row[0] if isinstance(row[0], UUID) else UUID(row[0]),
                    title=row[1],
                    author=row[2],
                    ingestion_status=row[3],
                    total_chunks=row[4],
                    created_at=str(row[5]),
                    updated_at=str(row[6]),
                )
            return None

    finally:
        await engine.dispose()


async def list_production_books() -> list[ProductionBook]:
    """
    List all books in production database.

    Returns:
        List of ProductionBook objects

    Raises:
        ValueError: If production database URL is not configured
    """
    if not settings.production_database_url:
        raise ValueError(
            "Production database URL not configured. "
            "Set PRODUCTION_DATABASE_URL in .env file."
        )

    logger.info("listing_production_books")

    # Create production database connection
    engine = create_async_engine(settings.production_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            query = text("""
                SELECT
                    b.id,
                    b.title,
                    b.author,
                    b.ingestion_status,
                    COUNT(c.id) as chunk_count,
                    b.created_at,
                    b.updated_at
                FROM books b
                LEFT JOIN chunks c ON c.book_id = b.id
                GROUP BY b.id, b.title, b.author, b.ingestion_status, b.created_at, b.updated_at
                ORDER BY b.created_at DESC
            """)

            result = await session.execute(query)
            rows = result.fetchall()

            return [
                ProductionBook(
                    id=row[0] if isinstance(row[0], UUID) else UUID(row[0]),
                    title=row[1],
                    author=row[2],
                    ingestion_status=row[3],
                    total_chunks=row[4],
                    created_at=str(row[5]),
                    updated_at=str(row[6]),
                )
                for row in rows
            ]

    finally:
        await engine.dispose()


async def generate_push_sql(book_id: UUID, session: AsyncSession) -> str:
    """
    Generate SQL statements for pushing book to production.

    Reuses export logic but returns SQL as string instead of writing to file.

    Args:
        book_id: UUID of book to push
        session: Local database session

    Returns:
        SQL statements as string

    Raises:
        ValueError: If book or required data not found
    """
    from datetime import datetime
    import json

    logger.info("generating_push_sql", book_id=str(book_id))

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

    # Build SQL
    sql_lines = []

    # Header
    sql_lines.append("-- ============================================")
    sql_lines.append("-- Minerva Knowledge Base Push to Production")
    sql_lines.append("-- ============================================")
    sql_lines.append(f"-- Book: {book.title}")
    if book.author:
        sql_lines.append(f"-- Author: {book.author}")
    sql_lines.append(f"-- Book ID: {book_id}")
    sql_lines.append(f"-- Pushed: {datetime.now().isoformat()}")
    sql_lines.append(f"-- Total Chunks: {len(chunks)}")
    sql_lines.append(f"-- Total Screenshots: {len(screenshots)}")
    sql_lines.append("-- ============================================")
    sql_lines.append("")

    # Transaction
    sql_lines.append("BEGIN;")
    sql_lines.append("")

    # Embedding configuration
    if embedding_config:
        sql_lines.append("-- Embedding Configuration")
        sql_lines.append(
            "INSERT INTO embedding_configs (id, model_name, model_version, dimensions, is_active, created_at)"
        )
        sql_lines.append(
            f"VALUES ('{embedding_config.id}', '{embedding_config.model_name}', "
            f"'{embedding_config.model_version or 'v1'}', {embedding_config.dimensions}, "
            f"{str(embedding_config.is_active).lower()}, '{embedding_config.created_at.isoformat()}')"
        )
        sql_lines.append("ON CONFLICT (id) DO NOTHING;")
        sql_lines.append("")

    # Book record
    sql_lines.append("-- Book Record")
    sql_lines.append(
        "INSERT INTO books (id, title, author, kindle_url, total_screenshots, "
        "capture_date, ingestion_status, metadata, created_at, updated_at)"
    )

    # Escape single quotes in text fields
    title = book.title.replace("'", "''") if book.title else ""
    author = book.author.replace("'", "''") if book.author else None
    kindle_url = book.kindle_url.replace("'", "''") if book.kindle_url else ""

    metadata_json = json.dumps(book.book_metadata) if book.book_metadata else "NULL"
    if metadata_json != "NULL":
        metadata_json = "'" + metadata_json.replace("'", "''") + "'"

    capture_date = f"'{book.capture_date.isoformat()}'" if book.capture_date else "NULL"

    author_sql = "NULL" if author is None else f"'{author}'"

    sql_lines.append(
        f"VALUES ('{book.id}', '{title}', "
        f"{author_sql}, '{kindle_url}', {book.total_screenshots}, "
        f"{capture_date}, '{book.ingestion_status}', "
        f"{metadata_json}, '{book.created_at.isoformat()}', '{book.updated_at.isoformat()}')"
    )
    sql_lines.append(
        "ON CONFLICT (id) DO UPDATE SET "
        "updated_at = EXCLUDED.updated_at, "
        "ingestion_status = EXCLUDED.ingestion_status, "
        "total_screenshots = EXCLUDED.total_screenshots;"
    )
    sql_lines.append("")

    # Screenshots
    if screenshots:
        sql_lines.append("-- Screenshots (metadata only, file_path = NULL)")
        for screenshot in screenshots:
            screenshot_hash = screenshot.screenshot_hash.replace("'", "''") if screenshot.screenshot_hash else None
            hash_sql = "NULL" if screenshot_hash is None else f"'{screenshot_hash}'"

            sql_lines.append(
                f"INSERT INTO screenshots (id, book_id, sequence_number, file_path, "
                f"screenshot_hash, captured_at)"
            )
            sql_lines.append(
                f"VALUES ('{screenshot.id}', '{screenshot.book_id}', {screenshot.sequence_number}, "
                f"NULL, {hash_sql}, '{screenshot.captured_at.isoformat()}')"
            )
            sql_lines.append("ON CONFLICT (id) DO NOTHING;")
        sql_lines.append("")

    # Chunks
    if chunks:
        sql_lines.append("-- Text Chunks with Embeddings")
        for chunk in chunks:
            chunk_text = chunk.chunk_text.replace("'", "''")

            # Format screenshot_ids array
            screenshot_ids_str = (
                "'{" + ",".join(str(sid) for sid in chunk.screenshot_ids) + "}'"
                if chunk.screenshot_ids
                else "NULL"
            )

            # Format embedding vector
            embedding_str = (
                "'[" + ",".join(str(e) for e in chunk.embedding) + "]'"
                if chunk.embedding
                else "NULL"
            )

            chunk_metadata = json.dumps(chunk.chunk_metadata) if chunk.chunk_metadata else "NULL"
            if chunk_metadata != "NULL":
                chunk_metadata = "'" + chunk_metadata.replace("'", "''") + "'"

            vision_model = chunk.vision_model.replace("'", "''") if chunk.vision_model else None

            embedding_config_sql = "NULL" if chunk.embedding_config_id is None else f"'{chunk.embedding_config_id}'"
            vision_model_sql = "NULL" if vision_model is None else f"'{vision_model}'"
            extraction_ts_sql = "NULL" if chunk.extraction_timestamp is None else f"'{chunk.extraction_timestamp.isoformat()}'"
            prompt_tokens_sql = "NULL" if chunk.vision_prompt_tokens is None else str(chunk.vision_prompt_tokens)
            completion_tokens_sql = "NULL" if chunk.vision_completion_tokens is None else str(chunk.vision_completion_tokens)

            sql_lines.append(
                f"INSERT INTO chunks (id, book_id, screenshot_ids, chunk_sequence, chunk_text, "
                f"chunk_token_count, embedding_config_id, embedding, vision_model, "
                f"vision_prompt_tokens, vision_completion_tokens, extraction_timestamp, "
                f"chunk_metadata, created_at)"
            )
            sql_lines.append(
                f"VALUES ('{chunk.id}', '{chunk.book_id}', {screenshot_ids_str}, "
                f"{chunk.chunk_sequence}, '{chunk_text}', {chunk.chunk_token_count}, "
                f"{embedding_config_sql}, {embedding_str}, {vision_model_sql}, "
                f"{prompt_tokens_sql}, {completion_tokens_sql}, {extraction_ts_sql}, "
                f"{chunk_metadata}, '{chunk.created_at.isoformat()}')"
            )
            sql_lines.append("ON CONFLICT (id) DO NOTHING;")
        sql_lines.append("")

    # Commit
    sql_lines.append("COMMIT;")

    return "\n".join(sql_lines)


async def push_book_to_production(
    book_id: UUID,
    local_session: AsyncSession,
    skip_if_exists: bool = False,
) -> dict[str, any]:
    """
    Push a book directly to production database.

    Args:
        book_id: UUID of book to push
        local_session: Local database session
        skip_if_exists: If True, skip push if book exists in production

    Returns:
        Dictionary with push results and metadata

    Raises:
        ValueError: If production database URL not configured or book not found
    """
    if not settings.production_database_url:
        raise ValueError(
            "Production database URL not configured. "
            "Set PRODUCTION_DATABASE_URL in .env file."
        )

    logger.info("pushing_book_to_production", book_id=str(book_id))

    # Validate book locally first
    report = await validate_and_report(book_id, local_session)

    # Check if book exists in production
    prod_book = await check_production_book_exists(book_id)

    if prod_book and skip_if_exists:
        logger.info("book_exists_in_production_skipping", book_id=str(book_id))
        return {
            "success": False,
            "skipped": True,
            "message": f"Book already exists in production: {prod_book.title}",
            "production_book": prod_book,
        }

    # Generate SQL
    sql = await generate_push_sql(book_id, local_session)

    # Execute SQL against production database
    engine = create_async_engine(settings.production_database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Execute SQL (already wrapped in transaction)
            await session.execute(text(sql))
            await session.commit()

            logger.info(
                "book_pushed_successfully",
                book_id=str(book_id),
                title=report.title,
                chunks=report.total_chunks,
            )

            return {
                "success": True,
                "skipped": False,
                "message": f"Successfully pushed '{report.title}' to production",
                "book_id": book_id,
                "title": report.title,
                "author": report.author,
                "total_chunks": report.total_chunks,
                "estimated_size_mb": report.estimated_size_mb,
                "existed_before": prod_book is not None,
            }

    except Exception as e:
        logger.error("push_failed", book_id=str(book_id), error=str(e))
        raise

    finally:
        await engine.dispose()


async def get_sync_status(local_session: AsyncSession) -> list[SyncStatus]:
    """
    Compare local and production databases to determine sync status.

    Returns a list of SyncStatus objects showing which books are:
    - local_only: Only in local database (need to push)
    - production_only: Only in production (from other computers)
    - synced: In both databases with same chunks
    - needs_update: In both but different chunk counts (possible update needed)

    Args:
        local_session: Local database session

    Returns:
        List of SyncStatus objects

    Raises:
        ValueError: If production database URL not configured
    """
    if not settings.production_database_url:
        raise ValueError(
            "Production database URL not configured. "
            "Set PRODUCTION_DATABASE_URL in .env file."
        )

    logger.info("comparing_local_and_production_databases")

    # Get local books
    from sqlalchemy import func

    local_query = (
        select(
            Book.id,
            Book.title,
            Book.author,
            Book.ingestion_status,
            Book.updated_at,
            func.count(Chunk.id).label("chunk_count")
        )
        .outerjoin(Chunk, Book.id == Chunk.book_id)
        .group_by(Book.id, Book.title, Book.author, Book.ingestion_status, Book.updated_at)
    )

    local_result = await local_session.execute(local_query)
    local_books = {
        row[0]: {  # book_id as key
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "status": row[3],
            "updated_at": str(row[4]) if row[4] else None,
            "chunks": row[5],
        }
        for row in local_result.fetchall()
    }

    # Get production books
    production_books_list = await list_production_books()
    production_books = {
        book.id: {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "status": book.ingestion_status,
            "updated_at": book.updated_at,
            "chunks": book.total_chunks,
        }
        for book in production_books_list
    }

    # Compare and build sync status
    sync_statuses = []
    all_book_ids = set(local_books.keys()) | set(production_books.keys())

    for book_id in all_book_ids:
        local_book = local_books.get(book_id)
        prod_book = production_books.get(book_id)

        if local_book and prod_book:
            # Book exists in both databases
            if local_book["chunks"] == prod_book["chunks"]:
                status = "synced"
            else:
                status = "needs_update"

            sync_statuses.append(
                SyncStatus(
                    book_id=book_id,
                    title=local_book["title"],
                    author=local_book["author"],
                    status=status,
                    local_chunks=local_book["chunks"],
                    production_chunks=prod_book["chunks"],
                    local_status=local_book["status"],
                    production_status=prod_book["status"],
                    local_updated=local_book["updated_at"],
                    production_updated=prod_book["updated_at"],
                )
            )
        elif local_book:
            # Only in local database
            sync_statuses.append(
                SyncStatus(
                    book_id=book_id,
                    title=local_book["title"],
                    author=local_book["author"],
                    status="local_only",
                    local_chunks=local_book["chunks"],
                    production_chunks=None,
                    local_status=local_book["status"],
                    production_status=None,
                    local_updated=local_book["updated_at"],
                    production_updated=None,
                )
            )
        else:
            # Only in production database
            sync_statuses.append(
                SyncStatus(
                    book_id=book_id,
                    title=prod_book["title"],
                    author=prod_book["author"],
                    status="production_only",
                    local_chunks=None,
                    production_chunks=prod_book["chunks"],
                    local_status=None,
                    production_status=prod_book["status"],
                    local_updated=None,
                    production_updated=prod_book["updated_at"],
                )
            )

    # Sort by status priority: local_only, needs_update, synced, production_only
    status_priority = {
        "local_only": 0,
        "needs_update": 1,
        "synced": 2,
        "production_only": 3,
    }
    sync_statuses.sort(key=lambda x: status_priority.get(x.status, 99))

    return sync_statuses
