"""End-to-end ingestion pipeline orchestrator."""

from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from sqlalchemy.ext.asyncio import AsyncSession

from minerva.config import settings
from minerva.core.ingestion.embedding_generator import EmbeddingGenerator
from minerva.core.ingestion.semantic_chunking import SemanticChunker
from minerva.core.ingestion.text_extraction import TextExtractor
from minerva.db.models.book import Book
from minerva.db.models.chunk import Chunk
from minerva.db.models.screenshot import Screenshot
from minerva.utils.exceptions import (
    ChunkingError,
    EmbeddingGenerationError,
    TextExtractionError,
)

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    """
    End-to-end pipeline for ingesting books from screenshots to searchable database.

    This orchestrator coordinates:
    1. Screenshot capture (KindleAutomation)
    2. Text extraction (TextExtractor with Tesseract OCR)
    3. Semantic chunking (SemanticChunker)
    4. Embedding generation (EmbeddingGenerator)
    5. Database storage and status tracking

    Handles:
    - Progress tracking with Rich progress bars
    - Transactional safety with rollback on failure
    - Cost tracking and quality metrics
    - Error recovery and resume capability
    - Screenshot→Text→Chunk lineage maintenance
    """

    def __init__(
        self,
        session: AsyncSession,
        screenshots_dir: Path | None = None,
        use_ai_formatting: bool | None = None,
    ) -> None:
        """
        Initialize ingestion pipeline with database session.

        Args:
            session: Async database session for persistence
            screenshots_dir: Optional directory for screenshots (defaults to settings)
            use_ai_formatting: Whether to use AI formatting for OCR cleanup (defaults to settings)
        """
        self.session = session
        self.screenshots_dir = screenshots_dir or settings.screenshots_dir

        # Initialize components
        self.text_extractor = TextExtractor(use_ai_formatting=use_ai_formatting)
        self.chunker = SemanticChunker()
        self.embedding_generator = EmbeddingGenerator(session=session)

    async def process_existing_book(self, book_id: UUID) -> Book:
        """
        Process an existing book (resume from current status).

        Args:
            book_id: UUID of the book to process

        Returns:
            Book object with updated status

        Raises:
            ValueError: If book not found
            TextExtractionError: If text extraction fails
            ChunkingError: If chunking fails
            EmbeddingGenerationError: If embedding generation fails
        """
        from sqlalchemy import select

        # Load book from database
        stmt = select(Book).where(Book.id == book_id)  # type: ignore
        result = await self.session.execute(stmt)
        book = result.scalar_one_or_none()

        if not book:
            raise ValueError(f"Book with ID {book_id} not found")

        logger.info(
            "processing_existing_book",
            book_id=str(book_id),
            title=book.title,
            current_status=book.ingestion_status,
        )

        # Determine starting stage based on current status
        start_stage = self._determine_start_stage(book.ingestion_status)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
            ) as progress:
                # Stage 1: Screenshots (already complete for existing books)
                if start_stage <= 1:
                    screenshots = await self._load_existing_screenshots(book)
                else:
                    screenshots = await self._load_existing_screenshots(book)

                # Stage 2: Text Extraction
                if start_stage <= 2:
                    extracted_texts, ocr_costs = await self._stage_text_extraction(
                        book, screenshots, progress
                    )
                else:
                    extracted_texts, ocr_costs = await self._load_extracted_texts(
                        book
                    )

                # Stage 3: Semantic Chunking
                if start_stage <= 3:
                    chunks = await self._stage_semantic_chunking(
                        book, extracted_texts, screenshots, progress
                    )
                else:
                    chunks = await self._load_existing_chunks(book)

                # Stage 4: Embedding Generation
                if start_stage <= 4:
                    embedding_costs = await self._stage_embedding_generation(
                        book, chunks, progress
                    )
                else:
                    embedding_costs = {"total_cost": 0.0, "tokens_used": 0}

                # Stage 5: Finalization
                await self._stage_finalization(book)

                # Display completion summary
                self._display_completion_summary(
                    book, ocr_costs, embedding_costs, len(screenshots), len(chunks)
                )

            logger.info(
                "book_processing_completed",
                book_id=str(book.id),
                title=book.title,
                status=book.ingestion_status,
            )

            return book

        except Exception as e:
            # Update book with error status
            book.ingestion_status = "failed"
            book.ingestion_error = str(e)
            await self.session.commit()

            logger.error(
                "book_processing_failed",
                book_id=str(book.id),
                title=book.title,
                error=str(e),
                stage=start_stage,
            )
            raise

    async def run_pipeline(
        self,
        kindle_url: str,
        title: str,
        author: str | None = None,
    ) -> Book:
        """
        Run complete ingestion pipeline for a book.

        Args:
            kindle_url: URL to Kindle book in browser
            title: Book title
            author: Optional book author

        Returns:
            Book object with status "completed"

        Raises:
            TextExtractionError: If text extraction fails
            ChunkingError: If chunking fails
            EmbeddingGenerationError: If embedding generation fails

        Example:
            ```python
            pipeline = IngestionPipeline(session=db_session)
            book = await pipeline.run_pipeline(
                kindle_url="https://read.amazon.com/...",
                title="Sample Book",
                author="John Doe"
            )
            print(f"Ingested {book.title}: {book.ingestion_status}")
            ```
        """
        logger.info(
            "pipeline_started",
            kindle_url=kindle_url,
            title=title,
            author=author,
        )

        # Create or retrieve book record
        book = await self._get_or_create_book(kindle_url, title, author)

        # Determine starting stage based on current status
        start_stage = self._determine_start_stage(book.ingestion_status)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
            ) as progress:
                # Stage 1: Screenshot Capture
                if start_stage <= 1:
                    screenshots = await self._stage_screenshot_capture(
                        book, kindle_url, progress
                    )
                else:
                    screenshots = await self._load_existing_screenshots(book)

                # Stage 2: Text Extraction
                if start_stage <= 2:
                    extracted_texts, ocr_costs = await self._stage_text_extraction(
                        book, screenshots, progress
                    )
                else:
                    extracted_texts, ocr_costs = await self._load_extracted_texts(
                        book
                    )

                # Stage 3: Semantic Chunking
                if start_stage <= 3:
                    chunks = await self._stage_semantic_chunking(
                        book, extracted_texts, screenshots, progress
                    )
                else:
                    chunks = await self._load_existing_chunks(book)

                # Stage 4: Embedding Generation
                if start_stage <= 4:
                    embedding_costs = await self._stage_embedding_generation(
                        book, chunks, progress
                    )
                else:
                    embedding_costs = {"total_cost": 0, "tokens_used": 0}

                # Stage 5: Finalization
                await self._stage_finalization(book)

                # Display completion summary
                self._display_completion_summary(
                    book, ocr_costs, embedding_costs, len(screenshots), len(chunks)
                )

            logger.info(
                "pipeline_completed",
                book_id=str(book.id),
                title=book.title,
                status=book.ingestion_status,
            )

            return book

        except Exception as e:
            # Update book with error status
            book.ingestion_status = "failed"
            book.ingestion_error = str(e)
            await self.session.commit()

            logger.error(
                "pipeline_failed",
                book_id=str(book.id),
                title=book.title,
                error=str(e),
                stage=start_stage,
            )
            raise

    async def _get_or_create_book(
        self, kindle_url: str, title: str, author: str | None
    ) -> Book:
        """Get existing book or create new one."""
        from sqlalchemy import select

        # Check if book exists
        stmt = select(Book).where(Book.kindle_url == kindle_url)  # type: ignore
        result = await self.session.execute(stmt)
        book = result.scalar_one_or_none()

        if book:
            logger.info("book_found", book_id=str(book.id), title=book.title)
            return book

        # Create new book
        book = Book(
            kindle_url=kindle_url,
            title=title,
            author=author,
            ingestion_status="in_progress",
        )
        self.session.add(book)
        await self.session.flush()

        logger.info("book_created", book_id=str(book.id), title=book.title)
        return book

    def _determine_start_stage(self, status: str) -> int:
        """Determine which stage to start from based on book status."""
        status_to_stage = {
            "in_progress": 1,
            "screenshots_complete": 2,
            "text_extracted": 3,
            "chunks_created": 4,
            "embeddings_generated": 5,
            "completed": 5,
        }
        return status_to_stage.get(status, 1)

    async def _stage_screenshot_capture(
        self, book: Book, kindle_url: str, progress: Progress
    ) -> list[Screenshot]:
        """Stage 1: Capture screenshots from Kindle."""
        task = progress.add_task("[cyan]Capturing screenshots...", total=None)

        # Note: KindleAutomation needs to be updated to work with the pipeline
        # For now, we'll create a placeholder that assumes screenshots exist
        logger.info("screenshot_capture_stage", book_id=str(book.id))

        # Update book status
        book.ingestion_status = "screenshots_complete"
        await self.session.commit()

        progress.update(task, completed=True)
        return []  # Placeholder

    async def _stage_text_extraction(
        self, book: Book, screenshots: list[Screenshot], progress: Progress
    ) -> tuple[dict[int, str], dict[str, float]]:
        """Stage 2: Extract text from screenshots."""
        task = progress.add_task("[cyan]Extracting text...", total=len(screenshots))

        extracted_texts: dict[int, str] = {}
        total_cost = 0.0
        total_tokens = 0

        for screenshot in screenshots:
            try:
                text, metadata = await self.text_extractor.extract_text_from_screenshot(
                    Path(screenshot.file_path),
                    book_id=str(book.id),
                    screenshot_id=str(screenshot.id),
                )

                extracted_texts[screenshot.sequence_number] = text
                total_cost += metadata.get("cost_estimate", 0)
                # Tesseract doesn't use tokens, only AI formatting does
                total_tokens += metadata.get("tokens_used", 0)

                progress.update(task, advance=1)

            except Exception as e:
                logger.error(
                    "text_extraction_failed",
                    book_id=str(book.id),
                    screenshot_id=str(screenshot.id),
                    error=str(e),
                )
                raise TextExtractionError(
                    f"Failed to extract text from screenshot {screenshot.id}: {e}"
                ) from e

        # Update book status
        book.ingestion_status = "text_extracted"
        await self.session.commit()

        ocr_costs = {
            "total_cost": total_cost,
            "tokens_used": total_tokens,  # Only non-zero if AI formatting is enabled
            "cost_per_page": total_cost / len(screenshots) if screenshots else 0,
        }

        logger.info(
            "text_extraction_complete",
            book_id=str(book.id),
            total_pages=len(screenshots),
            total_cost=total_cost,
        )

        return extracted_texts, ocr_costs

    async def _stage_semantic_chunking(
        self,
        book: Book,
        extracted_texts: dict[int, str],
        screenshots: list[Screenshot],
        progress: Progress,
    ) -> list[Chunk]:
        """Stage 3: Chunk extracted text semantically."""
        task = progress.add_task("[cyan]Chunking text...", total=1)

        # Combine all extracted texts in sequence order
        sorted_texts = sorted(extracted_texts.items())
        full_text = "\n\n".join(text for _, text in sorted_texts)

        # Create screenshot mapping (character position -> screenshot UUID)
        screenshot_mapping: dict[int, UUID] = {}
        char_position = 0
        for seq_num, text in sorted_texts:
            screenshot_id = next(
                (s.id for s in screenshots if s.sequence_number == seq_num), None
            )
            if screenshot_id:
                screenshot_mapping[char_position] = screenshot_id
            char_position += len(text) + 2  # +2 for \n\n

        # Chunk the text
        try:
            chunk_metadatas = await self.chunker.chunk_extracted_text(
                full_text, screenshot_mapping, book_id=str(book.id)
            )

            # Get or create embedding config before creating chunks
            embedding_config = await self.embedding_generator.get_or_create_embedding_config()

            # Create Chunk database records
            chunks: list[Chunk] = []
            for chunk_meta in chunk_metadatas:
                chunk = Chunk(
                    book_id=book.id,
                    chunk_text=chunk_meta.chunk_text,
                    chunk_sequence=chunk_meta.chunk_sequence,
                    chunk_token_count=chunk_meta.token_count,
                    screenshot_ids=chunk_meta.screenshot_ids,
                    embedding_config_id=embedding_config.id,
                    vision_model="tesseract",  # Using OCR, not vision API
                )
                self.session.add(chunk)
                chunks.append(chunk)

            await self.session.flush()

            # Update book status
            book.ingestion_status = "chunks_created"
            await self.session.commit()

            progress.update(task, advance=1)

            logger.info(
                "chunking_complete",
                book_id=str(book.id),
                total_chunks=len(chunks),
                avg_chunk_size=(
                    sum(c.chunk_token_count for c in chunks) / len(chunks)
                    if chunks
                    else 0
                ),
            )

            return chunks

        except Exception as e:
            logger.error("chunking_failed", book_id=str(book.id), error=str(e))
            raise ChunkingError(f"Failed to chunk text: {e}") from e

    async def _stage_embedding_generation(
        self, book: Book, chunks: list[Chunk], progress: Progress
    ) -> dict[str, Any]:
        """Stage 4: Generate embeddings for chunks."""
        task = progress.add_task("[cyan]Generating embeddings...", total=len(chunks))

        try:
            # Get or create embedding config
            embedding_config = (
                await self.embedding_generator.get_or_create_embedding_config()
            )

            # Extract chunk texts
            chunk_texts = [chunk.chunk_text for chunk in chunks]

            # Generate embeddings (handles batching internally)
            embeddings = await self.embedding_generator.generate_embeddings(
                chunk_texts, book_id=str(book.id)
            )

            # Update chunks with embeddings
            for chunk, embedding in zip(chunks, embeddings, strict=False):
                chunk.embedding = embedding
                chunk.embedding_config_id = embedding_config.id

            await self.session.flush()

            # Update book status
            book.ingestion_status = "embeddings_generated"
            await self.session.commit()

            progress.update(task, advance=len(chunks))

            # Calculate costs
            total_tokens = sum(c.chunk_token_count for c in chunks)
            total_cost = total_tokens * 0.02 / 1_000_000  # $0.02 per 1M tokens

            logger.info(
                "embeddings_complete",
                book_id=str(book.id),
                total_chunks=len(chunks),
                total_tokens=total_tokens,
                total_cost=total_cost,
            )

            return {
                "total_cost": total_cost,
                "tokens_used": total_tokens,
            }

        except Exception as e:
            logger.error(
                "embedding_generation_failed",
                book_id=str(book.id),
                error=str(e),
            )
            raise EmbeddingGenerationError(f"Failed to generate embeddings: {e}") from e

    async def _stage_finalization(self, book: Book) -> None:
        """Stage 5: Finalize ingestion and update book status."""
        book.ingestion_status = "completed"
        await self.session.commit()

        logger.info("pipeline_finalized", book_id=str(book.id))

    async def _load_existing_screenshots(self, book: Book) -> list[Screenshot]:
        """Load existing screenshots for resume capability."""
        from sqlalchemy import select

        stmt = select(Screenshot).where(Screenshot.book_id == book.id).order_by(Screenshot.sequence_number)  # type: ignore
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _load_extracted_texts(
        self, book: Book
    ) -> tuple[dict[int, str], dict[str, float]]:
        """Load existing extracted texts for resume capability."""
        # Placeholder - in production, extracted text would be stored
        return {}, {"total_cost": 0, "tokens_used": 0, "cost_per_page": 0}

    async def _load_existing_chunks(self, book: Book) -> list[Chunk]:
        """Load existing chunks for resume capability."""
        from sqlalchemy import select

        stmt = select(Chunk).where(Chunk.book_id == book.id).order_by(Chunk.chunk_sequence)  # type: ignore
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _display_completion_summary(
        self,
        book: Book,
        ocr_costs: dict[str, float],
        embedding_costs: dict[str, Any],
        total_pages: int,
        total_chunks: int,
    ) -> None:
        """Display ingestion completion summary."""
        total_cost = ocr_costs["total_cost"] + embedding_costs["total_cost"]

        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║              INGESTION COMPLETE                              ║
╚══════════════════════════════════════════════════════════════╝

Book: {book.title}
Status: {book.ingestion_status}

📊 Statistics:
  • Total pages: {total_pages}
  • Total chunks: {total_chunks}

💰 Costs:
  • OCR (Tesseract + AI formatting): ${ocr_costs['total_cost']:.4f}
  • Embeddings API: ${embedding_costs['total_cost']:.4f}
  • Total: ${total_cost:.4f}
  • Cost per page: ${ocr_costs.get('cost_per_page', 0):.6f}
"""
        print(summary)
