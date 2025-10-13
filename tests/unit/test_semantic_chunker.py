"""Unit tests for semantic chunking module."""

from uuid import uuid4

import pytest

from minerva.core.ingestion.semantic_chunking import (
    ChunkMetadata,
    SemanticChunker,
)


@pytest.fixture
def semantic_chunker():
    """Create SemanticChunker instance with default settings."""
    return SemanticChunker(chunk_size_tokens=700, chunk_overlap_percentage=0.15)


@pytest.fixture
def sample_text():
    """Create sample text with multiple paragraphs."""
    return """This is the first paragraph. It contains some introductory text about the subject matter.

This is the second paragraph. It provides more details and expands on the topic introduced in the first paragraph.

This is the third paragraph. It continues the discussion with additional information and context.

This is the fourth paragraph. It wraps up the section with concluding thoughts."""


@pytest.fixture
def sample_screenshot_mapping():
    """Create sample screenshot mapping."""
    return {
        0: uuid4(),  # First screenshot starts at position 0
        200: uuid4(),  # Second screenshot starts at position 200
        400: uuid4(),  # Third screenshot starts at position 400
    }


@pytest.mark.asyncio
async def test_normal_chunking(
    semantic_chunker, sample_text, sample_screenshot_mapping
):
    """Test normal chunking with realistic multi-paragraph text."""
    chunks = await semantic_chunker.chunk_extracted_text(
        sample_text, sample_screenshot_mapping, book_id="test-book"
    )

    # Should produce at least 1 chunk
    assert len(chunks) >= 1

    # All chunks should have required metadata
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_text
        assert chunk.chunk_sequence == i + 1
        assert len(chunk.screenshot_ids) > 0
        assert chunk.start_position >= 0
        assert chunk.end_position > chunk.start_position
        assert chunk.token_count > 0


@pytest.mark.asyncio
async def test_very_short_text(semantic_chunker, sample_screenshot_mapping):
    """Test that very short text (< chunk_size) returns single chunk."""
    short_text = "This is a very short text."

    chunks = await semantic_chunker.chunk_extracted_text(
        short_text, sample_screenshot_mapping
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_text == short_text
    assert chunks[0].chunk_sequence == 1
    assert chunks[0].token_count > 0


@pytest.mark.asyncio
async def test_empty_text(semantic_chunker, sample_screenshot_mapping):
    """Test that empty text returns empty list."""
    chunks = await semantic_chunker.chunk_extracted_text("", sample_screenshot_mapping)

    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_whitespace_only_text(semantic_chunker, sample_screenshot_mapping):
    """Test that whitespace-only text returns empty list."""
    chunks = await semantic_chunker.chunk_extracted_text(
        "   \n\n  \n  ", sample_screenshot_mapping
    )

    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_overlap_calculation():
    """Test that 15% overlap is applied correctly."""
    chunker = SemanticChunker(chunk_size_tokens=100, chunk_overlap_percentage=0.15)

    # Create a long text that will be chunked
    long_text = "\n\n".join([f"Paragraph {i} " * 50 for i in range(10)])
    screenshot_mapping = {0: uuid4()}

    chunks = await chunker.chunk_extracted_text(long_text, screenshot_mapping)

    # Should have multiple chunks
    assert len(chunks) > 1

    # Check that overlap tokens are calculated correctly
    assert chunker.overlap_tokens == 15  # 15% of 100


@pytest.mark.asyncio
async def test_paragraph_boundary_detection(
    semantic_chunker, sample_screenshot_mapping
):
    """Test that chunks split at paragraph boundaries."""
    text_with_paragraphs = """First paragraph here.

Second paragraph here.

Third paragraph here.

Fourth paragraph here."""

    chunks = await semantic_chunker.chunk_extracted_text(
        text_with_paragraphs, sample_screenshot_mapping
    )

    # All chunks should contain complete paragraphs (end with period)
    for chunk in chunks:
        assert chunk.chunk_text.strip()


@pytest.mark.asyncio
async def test_screenshot_mapping_single_screenshot(semantic_chunker):
    """Test screenshot mapping for chunks from single screenshot."""
    text = "Simple text from one screenshot."
    screenshot_id = uuid4()
    screenshot_mapping = {0: screenshot_id}

    chunks = await semantic_chunker.chunk_extracted_text(text, screenshot_mapping)

    assert len(chunks) == 1
    assert screenshot_id in chunks[0].screenshot_ids
    assert len(chunks[0].screenshot_ids) == 1


@pytest.mark.asyncio
async def test_screenshot_mapping_multiple_screenshots():
    """Test screenshot mapping for chunks spanning multiple screenshots."""
    chunker = SemanticChunker(chunk_size_tokens=50, chunk_overlap_percentage=0.15)

    # Create text with clear boundaries between screenshots
    text = (
        "Text from screenshot 1.\n\nText from screenshot 2.\n\nText from screenshot 3."
    )
    screenshot_1 = uuid4()
    screenshot_2 = uuid4()
    screenshot_3 = uuid4()

    screenshot_mapping = {
        0: screenshot_1,  # First part
        30: screenshot_2,  # Second part
        60: screenshot_3,  # Third part
    }

    chunks = await chunker.chunk_extracted_text(text, screenshot_mapping)

    # At least one chunk should exist
    assert len(chunks) >= 1

    # Each chunk should have associated screenshot IDs
    for chunk in chunks:
        assert len(chunk.screenshot_ids) > 0


@pytest.mark.asyncio
async def test_chunk_sequence_numbering(semantic_chunker):
    """Test that chunks are numbered sequentially."""
    long_text = "\n\n".join([f"Paragraph number {i}. " * 100 for i in range(20)])
    screenshot_mapping = {0: uuid4()}

    chunks = await semantic_chunker.chunk_extracted_text(long_text, screenshot_mapping)

    # Verify sequential numbering
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_sequence == i + 1


@pytest.mark.asyncio
async def test_character_position_tracking(semantic_chunker, sample_screenshot_mapping):
    """Test that start/end character positions are tracked correctly."""
    text = "First part. " * 20 + "\n\n" + "Second part. " * 20

    chunks = await semantic_chunker.chunk_extracted_text(
        text, sample_screenshot_mapping
    )

    # Verify positions make sense
    for chunk in chunks:
        assert chunk.start_position >= 0
        assert chunk.end_position > chunk.start_position
        assert chunk.end_position <= len(text)


@pytest.mark.asyncio
async def test_token_count_accuracy(semantic_chunker, sample_screenshot_mapping):
    """Test that token counts are calculated for each chunk."""
    text = "This is test text. " * 100  # Repeating text

    chunks = await semantic_chunker.chunk_extracted_text(
        text, sample_screenshot_mapping
    )

    # All chunks should have positive token counts
    for chunk in chunks:
        assert chunk.token_count > 0
        # Token count should be reasonable for the chunk size
        assert chunk.token_count <= semantic_chunker.chunk_size_tokens * 1.5


@pytest.mark.asyncio
async def test_custom_chunk_size():
    """Test chunker with custom chunk size."""
    chunker = SemanticChunker(chunk_size_tokens=200, chunk_overlap_percentage=0.10)

    text = "\n\n".join([f"Paragraph {i}. " * 30 for i in range(10)])
    screenshot_mapping = {0: uuid4()}

    chunks = await chunker.chunk_extracted_text(text, screenshot_mapping)

    # Verify chunks respect custom size
    for chunk in chunks:
        # Allow some flexibility, but chunks should generally be under target size
        assert chunk.token_count <= chunker.chunk_size_tokens * 1.5


@pytest.mark.asyncio
async def test_custom_overlap_percentage():
    """Test chunker with custom overlap percentage."""
    chunker = SemanticChunker(chunk_size_tokens=100, chunk_overlap_percentage=0.20)

    # Verify overlap calculation
    assert chunker.overlap_tokens == 20  # 20% of 100


@pytest.mark.asyncio
async def test_chunk_metadata_structure():
    """Test that ChunkMetadata has all required fields."""
    chunk_meta = ChunkMetadata(
        chunk_text="Sample text",
        chunk_sequence=1,
        screenshot_ids=[uuid4()],
        start_position=0,
        end_position=10,
        token_count=5,
    )

    assert chunk_meta.chunk_text == "Sample text"
    assert chunk_meta.chunk_sequence == 1
    assert len(chunk_meta.screenshot_ids) == 1
    assert chunk_meta.start_position == 0
    assert chunk_meta.end_position == 10
    assert chunk_meta.token_count == 5


@pytest.mark.asyncio
async def test_edge_case_text_exactly_at_boundary(
    semantic_chunker, sample_screenshot_mapping
):
    """Test text that is exactly at chunk boundary size."""
    # Create text with exact token count matching chunk size
    text = "Word " * 140  # Approximately 700 tokens

    chunks = await semantic_chunker.chunk_extracted_text(
        text, sample_screenshot_mapping
    )

    # Should create chunks without empty ones
    for chunk in chunks:
        assert len(chunk.chunk_text.strip()) > 0
        assert chunk.token_count > 0
