#!/usr/bin/env python3
"""Test script for real OpenAI API integration."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from minerva.core.ingestion.embedding_generator import EmbeddingGenerator
from minerva.core.ingestion.semantic_chunking import SemanticChunker
from minerva.core.ingestion.text_extraction import TextExtractor


def create_test_screenshot(output_path: Path) -> None:
    """Create a simple test screenshot with text."""
    # Create a white background image (typical Kindle page size)
    img = Image.new("RGB", (800, 1200), color="white")
    draw = ImageDraw.Draw(img)

    # Try to use a readable font, fall back to default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except Exception:
        font = ImageFont.load_default()

    # Add sample text (simulating a book page)
    text = """CHAPTER 1: Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that enables
systems to learn and improve from experience without being explicitly
programmed. The field has evolved significantly over the past decades.

Key Concepts:
• Supervised Learning: Learning from labeled data
• Unsupervised Learning: Finding patterns in unlabeled data
• Reinforcement Learning: Learning through trial and error

Applications of machine learning include natural language processing,
computer vision, recommendation systems, and autonomous vehicles.

The future of machine learning holds immense potential for transforming
industries and solving complex problems that were previously intractable."""

    # Draw text on image with proper spacing
    y_position = 50
    for line in text.split("\n"):
        draw.text((50, y_position), line, fill="black", font=font)
        y_position += 35

    # Save the image
    img.save(output_path)
    print(f"✓ Created test screenshot: {output_path}")


async def test_text_extraction(screenshot_path: Path) -> str:
    """Test TextExtractor with real Vision API."""
    print("\n" + "=" * 60)
    print("TEST 1: Text Extraction with OpenAI Vision API")
    print("=" * 60)

    extractor = TextExtractor()

    try:
        extracted_text, metadata = await extractor.extract_text_from_screenshot(
            screenshot_path,
            book_id="test-book-001",
            screenshot_id="test-screenshot-001",
        )

        print("\n✓ Text extraction successful!")
        print(f"  • Tokens used: {metadata['tokens_used']}")
        print(f"  • Cost estimate: ${metadata['cost_estimate']:.6f}")
        print(f"  • Vision model: {metadata['vision_model']}")

        print("\n📄 Extracted Text (first 500 chars):")
        print("-" * 60)
        print(extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)
        print("-" * 60)

        return extracted_text

    except Exception as e:
        print(f"\n✗ Text extraction failed: {e}")
        raise


async def test_semantic_chunking(text: str) -> list[str]:
    """Test SemanticChunker with extracted text."""
    print("\n" + "=" * 60)
    print("TEST 2: Semantic Chunking")
    print("=" * 60)

    chunker = SemanticChunker(chunk_size_tokens=100, chunk_overlap_percentage=0.15)

    # Create a simple screenshot mapping
    screenshot_mapping = {0: uuid4()}

    try:
        chunks = await chunker.chunk_extracted_text(
            text, screenshot_mapping, book_id="test-book-001"
        )

        print("\n✓ Chunking successful!")
        print(f"  • Total chunks: {len(chunks)}")
        print(
            f"  • Average chunk size: {sum(c.token_count for c in chunks) / len(chunks):.0f} tokens"
        )

        print("\n📦 Sample Chunks:")
        print("-" * 60)
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"\nChunk {i} (sequence {chunk.chunk_sequence}):")
            print(f"  • Token count: {chunk.token_count}")
            print(f"  • Position: {chunk.start_position}-{chunk.end_position}")
            print(f"  • Text preview: {chunk.chunk_text[:100]}...")

        if len(chunks) > 3:
            print(f"\n  ... and {len(chunks) - 3} more chunks")

        return [chunk.chunk_text for chunk in chunks]

    except Exception as e:
        print(f"\n✗ Chunking failed: {e}")
        raise


async def test_embedding_generation(chunk_texts: list[str]) -> None:
    """Test EmbeddingGenerator with real Embeddings API."""
    print("\n" + "=" * 60)
    print("TEST 3: Embedding Generation with OpenAI Embeddings API")
    print("=" * 60)

    # Create a mock session (we won't persist to database in this test)
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()

    generator = EmbeddingGenerator(
        session=mock_session, embedding_model="text-embedding-3-small"
    )

    try:
        embeddings = await generator.generate_embeddings(
            chunk_texts, book_id="test-book-001"
        )

        print("\n✓ Embedding generation successful!")
        print(f"  • Total embeddings: {len(embeddings)}")
        print(f"  • Embedding dimensions: {len(embeddings[0])} (expected: 1536)")

        # Calculate approximate cost
        total_tokens = sum(len(text.split()) * 1.3 for text in chunk_texts)
        cost_estimate = total_tokens * 0.02 / 1_000_000
        print(f"  • Approximate cost: ${cost_estimate:.6f}")

        print("\n🔢 Sample Embedding Vector (first 10 values):")
        print("-" * 60)
        print(embeddings[0][:10])
        print("...")

        # Verify embedding properties
        assert len(embeddings) == len(
            chunk_texts
        ), "Embedding count mismatch"
        assert all(
            len(emb) == 1536 for emb in embeddings
        ), "Incorrect embedding dimensions"

        print("\n✓ All embeddings have correct dimensions (1536)")

    except Exception as e:
        print(f"\n✗ Embedding generation failed: {e}")
        raise


async def main():
    """Run all API integration tests."""
    print("\n" + "=" * 60)
    print("REAL OpenAI API INTEGRATION TEST")
    print("=" * 60)
    print("\nThis will make real API calls and incur small costs (~$0.001)")
    print("Press Ctrl+C to cancel, or wait 3 seconds to continue...")

    # Wait 3 seconds to allow cancellation
    try:
        await asyncio.sleep(3)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        return

    # Create test screenshot
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    screenshot_path = screenshots_dir / "test_screenshot.png"
    create_test_screenshot(screenshot_path)

    try:
        # Test 1: Text Extraction
        extracted_text = await test_text_extraction(screenshot_path)

        # Test 2: Semantic Chunking
        chunk_texts = await test_semantic_chunking(extracted_text)

        # Test 3: Embedding Generation
        await test_embedding_generation(chunk_texts)

        # Summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ Text extraction with Vision API working")
        print("  ✓ Semantic chunking working")
        print("  ✓ Embedding generation with Embeddings API working")
        print("\nYour Epic 2 implementation is fully functional! 🎉")

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        if screenshot_path.exists():
            print(f"\n🧹 Cleaning up test file: {screenshot_path}")
            screenshot_path.unlink()


if __name__ == "__main__":
    asyncio.run(main())
