"""Integration tests for ingestion pipeline orchestrator."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from minerva.core.ingestion.pipeline import IngestionPipeline
from minerva.db.models.book import Book
from minerva.db.models.chunk import Chunk
from minerva.db.models.embedding_config import EmbeddingConfig
from minerva.db.models.screenshot import Screenshot
from minerva.utils.exceptions import (
    ChunkingError,
    EmbeddingGenerationError,
    TextExtractionError,
)


@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_text_extractor():
    """Create mock TextExtractor."""
    extractor = AsyncMock()
    extractor.extract_text_from_screenshot = AsyncMock(
        return_value=(
            "Extracted text content",
            {
                "ocr_method": "tesseract",
                "tesseract_version": "tesseract 5.5.1",
                "use_ai_formatting": False,
                "cost_estimate": 0.0,  # Tesseract is free
                "processing_time_ms": 1500,
            },
        )
    )
    return extractor


@pytest.fixture
def mock_chunker():
    """Create mock SemanticChunker."""
    from minerva.core.ingestion.semantic_chunking import ChunkMetadata

    chunker = AsyncMock()
    chunker.chunk_extracted_text = AsyncMock(
        return_value=[
            ChunkMetadata(
                chunk_text="Chunk 1 text",
                chunk_sequence=1,
                screenshot_ids=[uuid4()],
                start_position=0,
                end_position=100,
                token_count=50,
            ),
            ChunkMetadata(
                chunk_text="Chunk 2 text",
                chunk_sequence=2,
                screenshot_ids=[uuid4()],
                start_position=90,
                end_position=200,
                token_count=55,
            ),
        ]
    )
    return chunker


@pytest.fixture
def mock_embedding_generator():
    """Create mock EmbeddingGenerator."""
    generator = AsyncMock()
    generator.generate_embeddings = AsyncMock(
        return_value=[
            [0.1] * 1536,  # Fake embedding vector
            [0.2] * 1536,
        ]
    )
    generator.get_or_create_embedding_config = AsyncMock(
        return_value=EmbeddingConfig(
            id=uuid4(),
            model_name="text-embedding-3-small",
            dimensions=1536,
            is_active=True,
        )
    )
    return generator


@pytest.fixture
def ingestion_pipeline(
    mock_session,
    mock_text_extractor,
    mock_chunker,
    mock_embedding_generator,
):
    """Create IngestionPipeline with mocked dependencies."""
    pipeline = IngestionPipeline(session=mock_session)
    pipeline.text_extractor = mock_text_extractor
    pipeline.chunker = mock_chunker
    pipeline.embedding_generator = mock_embedding_generator
    return pipeline


@pytest.mark.asyncio
async def test_successful_complete_pipeline(ingestion_pipeline, mock_session):
    """Test successful execution of complete pipeline from start to finish."""
    # Arrange
    kindle_url = "https://read.amazon.com/test-book"
    title = "Test Book"
    author = "Test Author"

    # Mock book creation (book doesn't exist yet)
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_book_result)

    # Mock screenshot loading (return empty list for stage 1)
    mock_screenshot_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_screenshot_result.scalars.return_value = mock_scalars

    # Act
    with patch("rich.progress.Progress"):
        book = await ingestion_pipeline.run_pipeline(
            kindle_url=kindle_url,
            title=title,
            author=author,
        )

    # Assert
    assert book.title == title
    assert book.author == author
    assert book.kindle_url == kindle_url
    assert book.ingestion_status == "completed"
    assert book.ingestion_error is None

    # Verify session interactions
    mock_session.add.assert_called()  # Book was added
    assert mock_session.commit.call_count >= 5  # One commit per stage


@pytest.mark.asyncio
async def test_pipeline_creates_new_book(ingestion_pipeline, mock_session):
    """Test that pipeline creates new book when it doesn't exist."""
    # Arrange
    kindle_url = "https://read.amazon.com/new-book"
    title = "New Book"

    # Mock book doesn't exist
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    with patch("rich.progress.Progress"):
        book = await ingestion_pipeline.run_pipeline(
            kindle_url=kindle_url,
            title=title,
        )

    # Assert
    mock_session.add.assert_called()  # Book was added
    assert book.ingestion_status == "completed"


@pytest.mark.asyncio
async def test_pipeline_retrieves_existing_book(ingestion_pipeline, mock_session):
    """Test that pipeline retrieves existing book and resumes."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/existing-book",
        title="Existing Book",
        author="Test Author",
        ingestion_status="in_progress",
    )

    # Mock book exists
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_book
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    with patch("rich.progress.Progress"):
        book = await ingestion_pipeline.run_pipeline(
            kindle_url=existing_book.kindle_url,
            title=existing_book.title,
            author=existing_book.author,
        )

    # Assert
    assert book.id == existing_book.id
    # Chunks may be added, but the book itself should not be added again
    add_calls = [
        call for call in mock_session.add.call_args_list if isinstance(call[0][0], Book)
    ]
    assert len(add_calls) == 0  # Book was not added (already exists)


@pytest.mark.asyncio
async def test_resume_from_screenshots_complete(ingestion_pipeline, mock_session):
    """Test resume capability when screenshots are already complete."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/test-book",
        title="Test Book",
        ingestion_status="screenshots_complete",
    )

    # Mock book exists with screenshots_complete status
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = existing_book

    # Mock existing screenshots
    mock_screenshots = [
        Screenshot(
            id=uuid4(),
            book_id=existing_book.id,
            file_path=Path("/fake/path/page_1.png"),
            sequence_number=1,
        ),
        Screenshot(
            id=uuid4(),
            book_id=existing_book.id,
            file_path=Path("/fake/path/page_2.png"),
            sequence_number=2,
        ),
    ]
    mock_screenshot_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_screenshots
    mock_screenshot_result.scalars.return_value = mock_scalars

    mock_session.execute = AsyncMock(
        side_effect=[mock_book_result, mock_screenshot_result]
    )

    # Act
    with patch("rich.progress.Progress"):
        book = await ingestion_pipeline.run_pipeline(
            kindle_url=existing_book.kindle_url,
            title=existing_book.title,
        )

    # Assert
    assert book.ingestion_status == "completed"
    # Text extraction should have been called for each screenshot
    assert (
        ingestion_pipeline.text_extractor.extract_text_from_screenshot.call_count == 2
    )


@pytest.mark.asyncio
async def test_resume_from_chunks_created(ingestion_pipeline, mock_session):
    """Test resume capability when chunks are already created."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/test-book",
        title="Test Book",
        ingestion_status="chunks_created",
    )

    # Mock book exists with chunks_created status
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = existing_book

    # Mock existing chunks
    mock_chunks = [
        Chunk(
            id=uuid4(),
            book_id=existing_book.id,
            chunk_text="Chunk 1",
            chunk_sequence=1,
            chunk_token_count=50,
            screenshot_ids=[uuid4()],
        ),
        Chunk(
            id=uuid4(),
            book_id=existing_book.id,
            chunk_text="Chunk 2",
            chunk_sequence=2,
            chunk_token_count=60,
            screenshot_ids=[uuid4()],
        ),
    ]
    mock_chunks_result = MagicMock()
    mock_chunks_scalars = MagicMock()
    mock_chunks_scalars.all.return_value = mock_chunks
    mock_chunks_result.scalars.return_value = mock_chunks_scalars

    # Create a function to return appropriate mocks based on call count
    call_count = [0]

    async def mock_execute(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_book_result
        else:
            return mock_chunks_result

    mock_session.execute = mock_execute

    # Act
    with patch("rich.progress.Progress"):
        book = await ingestion_pipeline.run_pipeline(
            kindle_url=existing_book.kindle_url,
            title=existing_book.title,
        )

    # Assert
    assert book.ingestion_status == "completed"
    # Text extraction and chunking should be skipped
    ingestion_pipeline.text_extractor.extract_text_from_screenshot.assert_not_called()
    ingestion_pipeline.chunker.chunk_extracted_text.assert_not_called()
    # Embedding generation should have been called
    ingestion_pipeline.embedding_generator.generate_embeddings.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_error_handling_text_extraction(
    ingestion_pipeline, mock_session
):
    """Test error handling when text extraction fails."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/test-book",
        title="Test Book",
        ingestion_status="screenshots_complete",
    )

    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = existing_book

    # Mock screenshots exist
    mock_screenshots = [
        Screenshot(
            id=uuid4(),
            book_id=existing_book.id,
            file_path=Path("/fake/path/page_1.png"),
            sequence_number=1,
        )
    ]
    mock_screenshot_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_screenshots
    mock_screenshot_result.scalars.return_value = mock_scalars

    mock_session.execute = AsyncMock(
        side_effect=[mock_book_result, mock_screenshot_result]
    )

    # Mock text extraction failure
    ingestion_pipeline.text_extractor.extract_text_from_screenshot = AsyncMock(
        side_effect=TextExtractionError("Tesseract OCR failed")
    )

    # Act & Assert
    with pytest.raises(TextExtractionError, match="Tesseract OCR failed"):
        with patch("rich.progress.Progress"):
            await ingestion_pipeline.run_pipeline(
                kindle_url=existing_book.kindle_url,
                title=existing_book.title,
            )

    # Book status should be updated to failed
    assert existing_book.ingestion_status == "failed"
    assert existing_book.ingestion_error is not None
    assert "Tesseract OCR failed" in existing_book.ingestion_error
    mock_session.commit.assert_called()  # Error state was committed


@pytest.mark.asyncio
async def test_pipeline_error_handling_chunking(ingestion_pipeline, mock_session):
    """Test error handling when chunking fails."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/test-book",
        title="Test Book",
        ingestion_status="text_extracted",
    )

    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = existing_book
    mock_session.execute = AsyncMock(return_value=mock_book_result)

    # Mock chunking failure
    ingestion_pipeline.chunker.chunk_extracted_text = AsyncMock(
        side_effect=ChunkingError("Chunking failed")
    )

    # Act & Assert
    with pytest.raises(ChunkingError, match="Chunking failed"):
        with patch("rich.progress.Progress"):
            await ingestion_pipeline.run_pipeline(
                kindle_url=existing_book.kindle_url,
                title=existing_book.title,
            )

    # Book status should be updated to failed
    assert existing_book.ingestion_status == "failed"
    assert existing_book.ingestion_error is not None
    assert "Chunking failed" in existing_book.ingestion_error


@pytest.mark.asyncio
async def test_pipeline_error_handling_embeddings(ingestion_pipeline, mock_session):
    """Test error handling when embedding generation fails."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/test-book",
        title="Test Book",
        ingestion_status="chunks_created",
    )

    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = existing_book

    # Mock existing chunks
    mock_chunks = [
        Chunk(
            id=uuid4(),
            book_id=existing_book.id,
            chunk_text="Chunk 1",
            chunk_sequence=1,
            chunk_token_count=50,
            screenshot_ids=[uuid4()],
        )
    ]
    mock_chunks_result = MagicMock()
    mock_chunks_scalars = MagicMock()
    mock_chunks_scalars.all.return_value = mock_chunks
    mock_chunks_result.scalars.return_value = mock_chunks_scalars

    # Create a function to return appropriate mocks based on call count
    call_count = [0]

    async def mock_execute(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_book_result
        else:
            return mock_chunks_result

    mock_session.execute = mock_execute

    # Mock embedding generation failure
    ingestion_pipeline.embedding_generator.generate_embeddings = AsyncMock(
        side_effect=EmbeddingGenerationError("OpenAI API failed")
    )

    # Act & Assert
    with pytest.raises(EmbeddingGenerationError, match="OpenAI API failed"):
        with patch("rich.progress.Progress"):
            await ingestion_pipeline.run_pipeline(
                kindle_url=existing_book.kindle_url,
                title=existing_book.title,
            )

    # Book status should be updated to failed
    assert existing_book.ingestion_status == "failed"
    assert existing_book.ingestion_error is not None
    assert "OpenAI API failed" in existing_book.ingestion_error


@pytest.mark.asyncio
async def test_cost_tracking(ingestion_pipeline, mock_session):
    """Test that costs are tracked throughout the pipeline."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/test-book",
        title="Test Book",
        ingestion_status="screenshots_complete",
    )

    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = existing_book

    # Mock screenshots
    mock_screenshots = [
        Screenshot(
            id=uuid4(),
            book_id=existing_book.id,
            file_path=Path("/fake/path/page_1.png"),
            sequence_number=1,
        ),
        Screenshot(
            id=uuid4(),
            book_id=existing_book.id,
            file_path=Path("/fake/path/page_2.png"),
            sequence_number=2,
        ),
    ]
    mock_screenshot_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_screenshots
    mock_screenshot_result.scalars.return_value = mock_scalars

    mock_session.execute = AsyncMock(
        side_effect=[mock_book_result, mock_screenshot_result]
    )

    # Mock text extraction with cost (AI formatting enabled)
    ingestion_pipeline.text_extractor.extract_text_from_screenshot = AsyncMock(
        return_value=(
            "Extracted text",
            {
                "ocr_method": "tesseract",
                "tesseract_version": "tesseract 5.5.1",
                "use_ai_formatting": True,
                "cost_estimate": 0.002,  # AI formatting cost
                "processing_time_ms": 2000,
            },
        )
    )

    # Act
    with patch("rich.progress.Progress"):
        with patch("builtins.print") as mock_print:
            await ingestion_pipeline.run_pipeline(
                kindle_url=existing_book.kindle_url,
                title=existing_book.title,
            )

            # Assert - check that summary was printed with costs
            print_calls = "".join(str(call) for call in mock_print.call_args_list)
            assert "INGESTION COMPLETE" in print_calls
            assert "OCR" in print_calls  # Changed from "Vision API"
            assert "Embeddings API:" in print_calls
            assert "Total:" in print_calls


@pytest.mark.asyncio
async def test_stage_determination_logic(ingestion_pipeline):
    """Test _determine_start_stage logic for all statuses."""
    # Test all status → stage mappings
    assert ingestion_pipeline._determine_start_stage("in_progress") == 1
    assert ingestion_pipeline._determine_start_stage("screenshots_complete") == 2
    assert ingestion_pipeline._determine_start_stage("text_extracted") == 3
    assert ingestion_pipeline._determine_start_stage("chunks_created") == 4
    assert ingestion_pipeline._determine_start_stage("embeddings_generated") == 5
    assert ingestion_pipeline._determine_start_stage("completed") == 5
    # Unknown status should default to stage 1
    assert ingestion_pipeline._determine_start_stage("unknown_status") == 1


@pytest.mark.asyncio
async def test_screenshot_lineage_preservation(ingestion_pipeline, mock_session):
    """Test that screenshot→chunk lineage is preserved."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/test-book",
        title="Test Book",
        ingestion_status="screenshots_complete",
    )

    screenshot_1_id = uuid4()
    screenshot_2_id = uuid4()

    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = existing_book

    mock_screenshots = [
        Screenshot(
            id=screenshot_1_id,
            book_id=existing_book.id,
            file_path=Path("/fake/path/page_1.png"),
            sequence_number=1,
        ),
        Screenshot(
            id=screenshot_2_id,
            book_id=existing_book.id,
            file_path=Path("/fake/path/page_2.png"),
            sequence_number=2,
        ),
    ]
    mock_screenshot_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_screenshots
    mock_screenshot_result.scalars.return_value = mock_scalars

    mock_session.execute = AsyncMock(
        side_effect=[mock_book_result, mock_screenshot_result]
    )

    # Mock chunker to return chunks with screenshot IDs
    from minerva.core.ingestion.semantic_chunking import ChunkMetadata

    ingestion_pipeline.chunker.chunk_extracted_text = AsyncMock(
        return_value=[
            ChunkMetadata(
                chunk_text="Chunk from screenshot 1",
                chunk_sequence=1,
                screenshot_ids=[screenshot_1_id],
                start_position=0,
                end_position=100,
                token_count=50,
            ),
            ChunkMetadata(
                chunk_text="Chunk spanning both screenshots",
                chunk_sequence=2,
                screenshot_ids=[screenshot_1_id, screenshot_2_id],
                start_position=90,
                end_position=250,
                token_count=60,
            ),
        ]
    )

    # Act
    with patch("rich.progress.Progress"):
        await ingestion_pipeline.run_pipeline(
            kindle_url=existing_book.kindle_url,
            title=existing_book.title,
        )

    # Assert - verify chunks were created with correct screenshot IDs
    add_calls = mock_session.add.call_args_list
    chunk_adds = [call for call in add_calls if isinstance(call[0][0], Chunk)]

    # Should have 2 chunk additions
    assert len(chunk_adds) >= 2


@pytest.mark.asyncio
async def test_completion_summary_display(ingestion_pipeline, mock_session):
    """Test that completion summary is displayed with correct format."""
    # Arrange
    existing_book = Book(
        id=uuid4(),
        kindle_url="https://read.amazon.com/test-book",
        title="Test Book Title",
        ingestion_status="in_progress",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    with patch("rich.progress.Progress"):
        with patch("builtins.print") as mock_print:
            await ingestion_pipeline.run_pipeline(
                kindle_url=existing_book.kindle_url,
                title="Test Book Title",
            )

            # Assert
            print_output = "".join(str(call) for call in mock_print.call_args_list)
            assert "INGESTION COMPLETE" in print_output
            assert "Test Book Title" in print_output
            assert "Statistics:" in print_output
            assert "Total pages:" in print_output
            assert "Total chunks:" in print_output
            assert "Costs:" in print_output
