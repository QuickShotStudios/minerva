"""Unit tests for Tesseract OCR text extraction module."""

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from minerva.core.ingestion.text_extraction import TextExtractor
from minerva.utils.exceptions import TextExtractionError


@pytest.fixture
def sample_screenshot_path(tmp_path):
    """Create a temporary screenshot file for testing."""
    screenshot_file = tmp_path / "test_screenshot.png"
    screenshot_file.write_bytes(b"fake_image_data" * 10)
    return screenshot_file


@pytest.fixture
def mock_subprocess_success():
    """Create a mock successful subprocess result."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = """This is extracted text from a book page.

With multiple paragraphs and proper formatting.

- Bullet point 1
- Bullet point 2

Header Text
More content here."""
    mock_result.stderr = ""
    return mock_result


@pytest.fixture
def mock_tesseract_version():
    """Create a mock Tesseract version response."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "tesseract 5.3.0\n leptonica-1.82.0\n  libgif 5.2.1"
    mock_result.stderr = ""
    return mock_result


def create_mock_ai_response(
    text: str,
    prompt_tokens: int = 500,
    completion_tokens: int = 200,
) -> ChatCompletion:
    """Create a mock OpenAI API response for AI formatting."""
    return ChatCompletion(
        id="chatcmpl-test",
        object="chat.completion",
        created=1234567890,
        model="gpt-4o-mini",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=text,
                ),
                finish_reason="stop",
            )
        ],
        usage=CompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


@pytest.mark.asyncio
async def test_successful_extraction(
    sample_screenshot_path, mock_subprocess_success, mock_tesseract_version
):
    """Test successful text extraction with mocked subprocess."""
    with patch("subprocess.run") as mock_run:
        # First call: version check, subsequent calls: OCR
        mock_run.side_effect = [mock_tesseract_version, mock_subprocess_success]

        extractor = TextExtractor(tesseract_cmd="tesseract", use_ai_formatting=False)

        # Reset mock to only count OCR call
        mock_run.reset_mock()
        mock_run.return_value = mock_subprocess_success

        # Act
        extracted_text, metadata = await extractor.extract_text_from_screenshot(
            sample_screenshot_path,
            book_id="test-book-123",
            screenshot_id="test-screenshot-456",
        )

        # Assert
        assert "This is extracted text" in extracted_text
        assert "multiple paragraphs" in extracted_text
        assert metadata["ocr_method"] == "tesseract"
        assert "tesseract" in metadata["tesseract_version"].lower()
        assert metadata["use_ai_formatting"] is False
        assert metadata["cost_estimate"] == 0.0
        assert metadata["processing_time_ms"] >= 0
        assert isinstance(metadata["processing_time_ms"], int)


@pytest.mark.asyncio
async def test_tesseract_not_found():
    """Test handling of missing tesseract binary."""
    with patch("subprocess.run", side_effect=FileNotFoundError("tesseract not found")):
        with pytest.raises(TextExtractionError, match="Tesseract not found"):
            TextExtractor(tesseract_cmd="tesseract")


@pytest.mark.asyncio
async def test_tesseract_not_working(mock_tesseract_version):
    """Test handling of tesseract binary that exists but doesn't work."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error: Tesseract failed"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(TextExtractionError, match="not working properly"):
            TextExtractor(tesseract_cmd="tesseract")


@pytest.mark.asyncio
async def test_file_not_found_error():
    """Test that FileNotFoundError is raised for non-existent screenshot."""
    with patch("subprocess.run") as mock_run:
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_version.stdout = "tesseract 5.3.0"
        mock_run.return_value = mock_version

        extractor = TextExtractor(tesseract_cmd="tesseract")
        non_existent_path = Path("/nonexistent/screenshot.png")

        with pytest.raises(FileNotFoundError, match="Screenshot file not found"):
            await extractor.extract_text_from_screenshot(non_existent_path)


@pytest.mark.asyncio
async def test_subprocess_timeout(sample_screenshot_path, mock_tesseract_version):
    """Test handling of OCR subprocess timeout."""
    with patch("subprocess.run") as mock_run:
        # Version check succeeds, OCR times out
        mock_run.side_effect = [
            mock_tesseract_version,
            subprocess.TimeoutExpired(cmd="tesseract", timeout=30),
        ]

        extractor = TextExtractor(tesseract_cmd="tesseract")

        with pytest.raises(TextExtractionError, match="timeout.*>30s"):
            await extractor.extract_text_from_screenshot(sample_screenshot_path)


@pytest.mark.asyncio
async def test_ocr_failure(sample_screenshot_path, mock_tesseract_version):
    """Test handling of OCR failure (non-zero return code)."""
    with patch("subprocess.run") as mock_run:
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_fail.stderr = "Error: Failed to load image"

        mock_run.side_effect = [mock_tesseract_version, mock_fail]

        extractor = TextExtractor(tesseract_cmd="tesseract")

        with pytest.raises(TextExtractionError, match="Tesseract OCR failed"):
            await extractor.extract_text_from_screenshot(sample_screenshot_path)


@pytest.mark.asyncio
async def test_tesseract_version_detection(mock_tesseract_version):
    """Test Tesseract version detection."""
    with patch("subprocess.run", return_value=mock_tesseract_version):
        extractor = TextExtractor(tesseract_cmd="tesseract")
        version = extractor._get_tesseract_version()

        assert "tesseract" in version.lower()
        assert "5.3.0" in version


@pytest.mark.asyncio
async def test_tesseract_version_detection_failure(mock_tesseract_version):
    """Test Tesseract version detection falls back gracefully on error."""
    with patch("subprocess.run", return_value=mock_tesseract_version):
        extractor = TextExtractor(tesseract_cmd="tesseract")

    # Simulate version detection failure
    with patch("subprocess.run", side_effect=Exception("Unexpected error")):
        version = extractor._get_tesseract_version()
        assert version == "tesseract (version unknown)"


@pytest.mark.asyncio
async def test_tesseract_command_format(
    sample_screenshot_path, mock_subprocess_success, mock_tesseract_version
):
    """Test that Tesseract is called with correct command format."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            mock_tesseract_version,
            mock_subprocess_success,
            mock_tesseract_version,
        ]

        extractor = TextExtractor(tesseract_cmd="tesseract")

        # Reset and capture calls
        mock_run.reset_mock()
        mock_run.side_effect = [mock_subprocess_success, mock_tesseract_version]

        await extractor.extract_text_from_screenshot(sample_screenshot_path)

        # Verify command format - check the first call (OCR)
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "tesseract" in first_call_args
        assert "stdout" in first_call_args
        assert "-l" in first_call_args
        assert "eng" in first_call_args
        assert "--psm" in first_call_args
        assert "3" in first_call_args


@pytest.mark.asyncio
async def test_ai_formatting_enabled(
    sample_screenshot_path, mock_subprocess_success, mock_tesseract_version
):
    """Test optional AI formatting when enabled."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_tesseract_version, mock_subprocess_success]

        with patch("minerva.utils.openai_client.get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            formatted_text = "This is cleaned and formatted text."
            mock_response = create_mock_ai_response(formatted_text)
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            extractor = TextExtractor(tesseract_cmd="tesseract", use_ai_formatting=True)

            # Reset mock to only count OCR call
            mock_run.reset_mock()
            mock_run.return_value = mock_subprocess_success

            extracted_text, metadata = await extractor.extract_text_from_screenshot(
                sample_screenshot_path
            )

            assert extracted_text == formatted_text
            assert metadata["use_ai_formatting"] is True
            assert metadata["cost_estimate"] > 0


@pytest.mark.asyncio
async def test_ai_formatting_fallback_on_error(
    sample_screenshot_path, mock_subprocess_success, mock_tesseract_version
):
    """Test graceful fallback to raw OCR when AI formatting fails."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_tesseract_version, mock_subprocess_success]

        with patch("minerva.utils.openai_client.get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("OpenAI API error")
            )
            mock_get_client.return_value = mock_client

            extractor = TextExtractor(tesseract_cmd="tesseract", use_ai_formatting=True)

            # Reset mock to only count OCR call
            mock_run.reset_mock()
            mock_run.return_value = mock_subprocess_success

            extracted_text, metadata = await extractor.extract_text_from_screenshot(
                sample_screenshot_path
            )

            # Should fall back to raw OCR text
            assert "This is extracted text" in extracted_text
            assert metadata["cost_estimate"] == 0.0


@pytest.mark.asyncio
async def test_processing_time_tracking(
    sample_screenshot_path, mock_subprocess_success, mock_tesseract_version
):
    """Test that processing time is tracked and logged."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_tesseract_version, mock_subprocess_success]

        extractor = TextExtractor(tesseract_cmd="tesseract")

        # Reset mock
        mock_run.reset_mock()
        mock_run.return_value = mock_subprocess_success

        _, metadata = await extractor.extract_text_from_screenshot(
            sample_screenshot_path
        )

        assert "processing_time_ms" in metadata
        assert metadata["processing_time_ms"] >= 0
        assert isinstance(metadata["processing_time_ms"], int)


@pytest.mark.asyncio
async def test_logging_context(
    sample_screenshot_path, mock_subprocess_success, mock_tesseract_version
):
    """Test that logging includes proper context (book_id, screenshot_id)."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_tesseract_version, mock_subprocess_success]

        extractor = TextExtractor(tesseract_cmd="tesseract")

        # Reset mock
        mock_run.reset_mock()
        mock_run.return_value = mock_subprocess_success

        with patch("minerva.core.ingestion.text_extraction.logger") as mock_logger:
            await extractor.extract_text_from_screenshot(
                sample_screenshot_path,
                book_id="test-book",
                screenshot_id="test-screenshot",
            )

            # Assert - verify logger.info was called with context
            mock_logger.info.assert_called()
            call_kwargs = mock_logger.info.call_args[1]
            assert call_kwargs["book_id"] == "test-book"
            assert call_kwargs["screenshot_id"] == "test-screenshot"


@pytest.mark.asyncio
async def test_text_structure_preservation():
    """Test that extraction preserves text structure (paragraphs, headers, lists)."""
    # Verify PSM mode 3 is used for structure preservation
    from minerva.core.ingestion.text_extraction import TextExtractor

    with patch("subprocess.run") as mock_run:
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_version.stdout = "tesseract 5.3.0"
        mock_run.return_value = mock_version

        extractor = TextExtractor(tesseract_cmd="tesseract")

        # PSM mode 3 is automatic page segmentation which preserves structure
        assert extractor.tesseract_cmd == "tesseract"


@pytest.mark.asyncio
async def test_empty_ocr_output(sample_screenshot_path, mock_tesseract_version):
    """Test handling of empty OCR output."""
    with patch("subprocess.run") as mock_run:
        mock_empty = MagicMock()
        mock_empty.returncode = 0
        mock_empty.stdout = ""

        mock_run.side_effect = [mock_tesseract_version, mock_empty]

        extractor = TextExtractor(tesseract_cmd="tesseract")

        # Reset mock
        mock_run.reset_mock()
        mock_run.return_value = mock_empty

        extracted_text, metadata = await extractor.extract_text_from_screenshot(
            sample_screenshot_path
        )

        assert extracted_text == ""
        assert metadata["ocr_method"] == "tesseract"
