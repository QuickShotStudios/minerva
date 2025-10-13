"""Semantic text chunking with configurable overlap for optimal vector search."""

from uuid import UUID

import structlog

from minerva.config import settings
from minerva.utils.exceptions import ChunkingError
from minerva.utils.token_counter import count_tokens

logger = structlog.get_logger(__name__)


class ChunkMetadata:
    """Metadata for a single text chunk."""

    def __init__(
        self,
        chunk_text: str,
        chunk_sequence: int,
        screenshot_ids: list[UUID],
        start_position: int,
        end_position: int,
        token_count: int,
    ):
        """
        Initialize chunk metadata.

        Args:
            chunk_text: The actual chunk text content
            chunk_sequence: Order of chunk within book (1, 2, 3...)
            screenshot_ids: Array of screenshot UUIDs this chunk spans
            start_position: Start character position in source text
            end_position: End character position in source text
            token_count: Actual token count using tiktoken
        """
        self.chunk_text = chunk_text
        self.chunk_sequence = chunk_sequence
        self.screenshot_ids = screenshot_ids
        self.start_position = start_position
        self.end_position = end_position
        self.token_count = token_count


class SemanticChunker:
    """
    Semantic text chunker with configurable overlap.

    This class handles:
    - Text chunking at natural boundaries (paragraphs, sections)
    - Configurable chunk size (default: 500-800 tokens)
    - Configurable overlap between chunks (default: 15%)
    - Token counting using tiktoken
    - Screenshot-to-chunk mapping
    - Metadata tracking (sequence, positions, token counts)
    """

    def __init__(
        self,
        chunk_size_tokens: int | None = None,
        chunk_overlap_percentage: float | None = None,
    ) -> None:
        """
        Initialize SemanticChunker with configuration.

        Args:
            chunk_size_tokens: Target chunk size in tokens (defaults to settings value)
            chunk_overlap_percentage: Overlap percentage as decimal (defaults to settings value)
        """
        # Get chunk size from settings or use provided value
        if chunk_size_tokens is None:
            # Use default from settings if available, otherwise 700
            self.chunk_size_tokens = getattr(settings, "chunk_size_tokens", 700)
        else:
            self.chunk_size_tokens = chunk_size_tokens

        # Get overlap percentage from settings or use provided value
        if chunk_overlap_percentage is None:
            # Use default from settings if available, otherwise 0.15 (15%)
            self.chunk_overlap_percentage = getattr(
                settings, "chunk_overlap_percentage", 0.15
            )
        else:
            self.chunk_overlap_percentage = chunk_overlap_percentage

        # Calculate overlap size in tokens
        self.overlap_tokens = int(
            self.chunk_size_tokens * self.chunk_overlap_percentage
        )

    async def chunk_extracted_text(
        self,
        text: str,
        screenshot_mapping: dict[int, UUID],
        book_id: str | None = None,
    ) -> list[ChunkMetadata]:
        """
        Chunk extracted text into semantic segments with overlap.

        Args:
            text: Full extracted text from all screenshots
            screenshot_mapping: Dict mapping character positions to screenshot UUIDs
                               Format: {start_char_pos: screenshot_uuid}
            book_id: Optional book ID for logging context

        Returns:
            List of ChunkMetadata objects with chunk text, sequence, and metadata

        Raises:
            ChunkingError: If chunking fails

        Example:
            ```python
            chunker = SemanticChunker()
            screenshot_mapping = {
                0: UUID("screenshot-1"),
                1000: UUID("screenshot-2"),
                2000: UUID("screenshot-3")
            }
            chunks = await chunker.chunk_extracted_text(
                "Full book text...",
                screenshot_mapping,
                book_id="book-123"
            )
            ```
        """
        if not text or not text.strip():
            logger.warning("empty_text_for_chunking", book_id=book_id)
            return []

        try:
            # Split text into paragraphs (natural boundaries)
            paragraphs = self._split_into_paragraphs(text)

            # Build chunks with overlap
            chunks = self._build_chunks_with_overlap(
                paragraphs, text, screenshot_mapping
            )

            logger.info(
                "chunking_complete",
                book_id=book_id,
                total_chunks=len(chunks),
                avg_chunk_size=(
                    sum(c.token_count for c in chunks) / len(chunks) if chunks else 0
                ),
                total_text_length=len(text),
            )

            return chunks

        except Exception as e:
            logger.error(
                "chunking_failed",
                book_id=book_id,
                error=str(e),
                text_length=len(text),
            )
            raise ChunkingError(f"Failed to chunk text: {e}") from e

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """
        Split text into paragraphs at natural boundaries.

        Args:
            text: Text to split

        Returns:
            List of paragraph strings
        """
        # Split on double newlines (paragraph breaks)
        paragraphs = text.split("\n\n")

        # Filter out empty paragraphs and strip whitespace
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _build_chunks_with_overlap(
        self,
        paragraphs: list[str],
        full_text: str,
        screenshot_mapping: dict[int, UUID],
    ) -> list[ChunkMetadata]:
        """
        Build chunks from paragraphs with overlap.

        Args:
            paragraphs: List of paragraph strings
            full_text: Original full text for position tracking
            screenshot_mapping: Dict mapping character positions to screenshot UUIDs

        Returns:
            List of ChunkMetadata objects
        """
        chunks: list[ChunkMetadata] = []
        current_chunk_paragraphs: list[str] = []
        chunk_sequence = 1
        text_position = 0

        for paragraph in paragraphs:
            # Check if adding this paragraph would exceed chunk size
            potential_chunk = (
                "\n\n".join(current_chunk_paragraphs + [paragraph])
                if current_chunk_paragraphs
                else paragraph
            )
            potential_tokens = count_tokens(potential_chunk)

            if potential_tokens > self.chunk_size_tokens and current_chunk_paragraphs:
                # Finalize current chunk
                chunk_text = "\n\n".join(current_chunk_paragraphs)
                chunk_start = text_position
                chunk_end = text_position + len(chunk_text)

                # Determine screenshot IDs for this chunk
                screenshot_ids = self._get_screenshot_ids_for_range(
                    chunk_start, chunk_end, screenshot_mapping
                )

                # Create chunk metadata
                chunk_metadata = ChunkMetadata(
                    chunk_text=chunk_text,
                    chunk_sequence=chunk_sequence,
                    screenshot_ids=screenshot_ids,
                    start_position=chunk_start,
                    end_position=chunk_end,
                    token_count=count_tokens(chunk_text),
                )
                chunks.append(chunk_metadata)

                # Calculate overlap text (last N% of previous chunk)
                overlap_text = self._calculate_overlap_text(chunk_text)

                # Start new chunk with overlap
                current_chunk_paragraphs = [overlap_text, paragraph]
                chunk_sequence += 1
                text_position = chunk_end

            else:
                # Add paragraph to current chunk
                current_chunk_paragraphs.append(paragraph)

        # Handle final chunk
        if current_chunk_paragraphs:
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            chunk_start = text_position if chunks else 0
            chunk_end = chunk_start + len(chunk_text)

            screenshot_ids = self._get_screenshot_ids_for_range(
                chunk_start, chunk_end, screenshot_mapping
            )

            chunk_metadata = ChunkMetadata(
                chunk_text=chunk_text,
                chunk_sequence=chunk_sequence,
                screenshot_ids=screenshot_ids,
                start_position=chunk_start,
                end_position=chunk_end,
                token_count=count_tokens(chunk_text),
            )
            chunks.append(chunk_metadata)

        return chunks

    def _calculate_overlap_text(self, chunk_text: str) -> str:
        """
        Calculate overlap text from previous chunk (last N% of text).

        Args:
            chunk_text: Previous chunk text

        Returns:
            Overlap text (last N% by tokens)
        """
        tokens_in_chunk = count_tokens(chunk_text)
        if tokens_in_chunk <= self.overlap_tokens:
            # If chunk is smaller than overlap, use entire chunk
            return chunk_text

        # Split by words and calculate approximate overlap
        words = chunk_text.split()
        total_words = len(words)
        # Approximate: take last N% of words
        overlap_word_count = int(total_words * self.chunk_overlap_percentage)
        if overlap_word_count == 0:
            overlap_word_count = 1

        overlap_words = words[-overlap_word_count:]
        return " ".join(overlap_words)

    def _get_screenshot_ids_for_range(
        self,
        start_pos: int,
        end_pos: int,
        screenshot_mapping: dict[int, UUID],
    ) -> list[UUID]:
        """
        Get screenshot IDs for a character range.

        Args:
            start_pos: Start character position
            end_pos: End character position
            screenshot_mapping: Dict mapping character positions to screenshot UUIDs

        Returns:
            List of screenshot UUIDs (typically 1, sometimes 2 for overlapping chunks)
        """
        screenshot_ids: set[UUID] = set()

        # Sort mapping keys to find which screenshots this range spans
        sorted_positions = sorted(screenshot_mapping.keys())

        for pos in sorted_positions:
            # Check if this screenshot position falls within our chunk range
            if pos <= end_pos:
                screenshot_ids.add(screenshot_mapping[pos])

                # If we've gone past the start position, we can stop
                # (we only care about screenshots that overlap with this chunk)
                if pos >= start_pos:
                    # Get the next screenshot position to check if chunk spans multiple
                    idx = sorted_positions.index(pos)
                    if idx + 1 < len(sorted_positions):
                        next_pos = sorted_positions[idx + 1]
                        if next_pos <= end_pos:
                            screenshot_ids.add(screenshot_mapping[next_pos])

        return list(screenshot_ids)
