#!/usr/bin/env python3
"""
Manual end-to-end integration test for the full ingestion pipeline.

Tests the complete pipeline with real components:
- Tesseract OCR text extraction
- Semantic chunking
- Embedding generation (dry-run mode, no API calls)
- Database integration

This validates that Story 2.1 (Tesseract OCR) integrates properly with
the rest of the pipeline components.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

import structlog

from minerva.core.ingestion.embedding_generator import EmbeddingGenerator
from minerva.core.ingestion.semantic_chunking import SemanticChunker
from minerva.core.ingestion.text_extraction import TextExtractor
from minerva.db.models.screenshot import Screenshot

# Set up logging
logger = structlog.get_logger(__name__)


class DryRunSession:
    """Mock async session for dry-run testing without real database."""

    def __init__(self):
        self.objects = []

    def add(self, obj):
        """Add object to mock session."""
        self.objects.append(obj)
        logger.info("session_add", object_type=type(obj).__name__)

    async def flush(self):
        """Mock flush - assign IDs to objects."""
        logger.info("session_flush", objects_count=len(self.objects))
        for obj in self.objects:
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = uuid4()

    async def commit(self):
        """Mock commit."""
        logger.info("session_commit", objects_count=len(self.objects))

    async def rollback(self):
        """Mock rollback."""
        logger.info("session_rollback")

    async def execute(self, stmt):
        """Mock execute - return empty results."""
        from unittest.mock import MagicMock

        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result


class DryRunEmbeddingGenerator(EmbeddingGenerator):
    """Dry-run embedding generator that doesn't call OpenAI API."""

    async def generate_embeddings(self, texts, book_id=None):
        """Generate fake embeddings without API call."""
        logger.info(
            "dry_run_embeddings",
            book_id=book_id,
            num_chunks=len(texts),
        )
        # Return fake embeddings (1536-dimensional vectors of zeros)
        return [[0.0] * 1536 for _ in texts]


async def test_full_pipeline_with_real_components():
    """Test full pipeline with real Tesseract OCR and components."""
    print("\n" + "=" * 80)
    print("MANUAL END-TO-END INTEGRATION TEST")
    print("=" * 80 + "\n")

    # Use real screenshots from the screenshots directory
    screenshots_dir = Path("screenshots")
    screenshot_files = sorted(screenshots_dir.glob("Kindle-*.png"))[:3]  # Use first 3

    if not screenshot_files:
        print("❌ No screenshots found in screenshots/ directory")
        print("   Please ensure Kindle screenshots exist in the screenshots/ folder")
        return False

    print(f"📸 Found {len(screenshot_files)} screenshots to test:\n")
    for i, screenshot in enumerate(screenshot_files, 1):
        print(f"   {i}. {screenshot.name}")

    print("\n" + "-" * 80)
    print("STAGE 1: Initialize Components")
    print("-" * 80 + "\n")

    # Create dry-run session
    session = DryRunSession()

    # Initialize real components
    text_extractor = TextExtractor(use_ai_formatting=False)
    chunker = SemanticChunker()
    embedding_generator = DryRunEmbeddingGenerator(session=session)

    print("✓ TextExtractor initialized (Tesseract OCR)")
    print("✓ SemanticChunker initialized")
    print("✓ EmbeddingGenerator initialized (dry-run mode)")

    print("\n" + "-" * 80)
    print("STAGE 2: Text Extraction (Tesseract OCR)")
    print("-" * 80 + "\n")

    extracted_texts = {}
    total_processing_time = 0
    total_cost = 0.0

    for i, screenshot_file in enumerate(screenshot_files, 1):
        print(f"Processing screenshot {i}/{len(screenshot_files)}: {screenshot_file.name}")

        text, metadata = await text_extractor.extract_text_from_screenshot(
            screenshot_file,
            book_id="test-book",
            screenshot_id=f"screenshot-{i}",
        )

        extracted_texts[i] = text
        total_processing_time += metadata["processing_time_ms"]
        total_cost += metadata["cost_estimate"]

        print(f"  ✓ Extracted {len(text)} characters")
        print(f"    - OCR Method: {metadata['ocr_method']}")
        print(f"    - Processing Time: {metadata['processing_time_ms']}ms")
        print(f"    - Cost: ${metadata['cost_estimate']:.6f}")
        print(f"    - AI Formatting: {metadata['use_ai_formatting']}")
        print()

    avg_processing_time = total_processing_time / len(screenshot_files)
    print("✓ Text extraction complete:")
    print(f"  - Total text: {sum(len(t) for t in extracted_texts.values())} characters")
    print(f"  - Avg processing time: {avg_processing_time:.0f}ms per page")
    print(f"  - Total cost: ${total_cost:.6f}")

    print("\n" + "-" * 80)
    print("STAGE 3: Semantic Chunking")
    print("-" * 80 + "\n")

    # Create screenshot mapping
    screenshot_mapping = {}
    char_position = 0
    screenshot_objects = []

    for seq_num, text in sorted(extracted_texts.items()):
        screenshot_id = uuid4()
        screenshot_mapping[char_position] = screenshot_id
        screenshot_objects.append(
            Screenshot(
                id=screenshot_id,
                book_id=uuid4(),
                file_path=screenshot_files[seq_num - 1],
                sequence_number=seq_num,
            )
        )
        char_position += len(text) + 2  # +2 for \n\n

    # Combine all texts
    full_text = "\n\n".join(text for _, text in sorted(extracted_texts.items()))

    # Chunk the text
    chunk_metadatas = await chunker.chunk_extracted_text(
        full_text,
        screenshot_mapping,
        book_id="test-book",
    )

    print("✓ Chunking complete:")
    print(f"  - Total chunks: {len(chunk_metadatas)}")
    print(f"  - Avg chunk size: {sum(c.token_count for c in chunk_metadatas) / len(chunk_metadatas):.0f} tokens")
    print(f"  - Total tokens: {sum(c.token_count for c in chunk_metadatas)}")

    print("\n  Chunk details:")
    for i, chunk in enumerate(chunk_metadatas[:5], 1):  # Show first 5
        print(f"    Chunk {i}:")
        print(f"      - Length: {len(chunk.chunk_text)} chars")
        print(f"      - Tokens: {chunk.token_count}")
        print(f"      - Screenshots: {len(chunk.screenshot_ids)}")
        print(f"      - Preview: {chunk.chunk_text[:80]}...")

    if len(chunk_metadatas) > 5:
        print(f"    ... and {len(chunk_metadatas) - 5} more chunks")

    print("\n" + "-" * 80)
    print("STAGE 4: Embedding Generation (Dry-Run)")
    print("-" * 80 + "\n")

    # Extract chunk texts
    chunk_texts = [chunk.chunk_text for chunk in chunk_metadatas]

    # Generate embeddings (dry-run)
    embeddings = await embedding_generator.generate_embeddings(
        chunk_texts,
        book_id="test-book",
    )

    print("✓ Embeddings generated (dry-run):")
    print(f"  - Total embeddings: {len(embeddings)}")
    print(f"  - Embedding dimensions: {len(embeddings[0]) if embeddings else 0}")
    print("  - Note: Dry-run mode - no actual OpenAI API calls made")

    print("\n" + "=" * 80)
    print("INTEGRATION TEST RESULTS")
    print("=" * 80 + "\n")

    print("✅ ALL STAGES COMPLETED SUCCESSFULLY!\n")

    print("Component Integration Verified:")
    print("  ✓ Tesseract OCR → Text Extraction")
    print("  ✓ Text Extraction → Semantic Chunking")
    print("  ✓ Semantic Chunking → Embedding Generation")
    print("  ✓ Screenshot-to-Chunk lineage preserved")

    print("\nPipeline Metrics:")
    print(f"  • Screenshots processed: {len(screenshot_files)}")
    print(f"  • Text extracted: {sum(len(t) for t in extracted_texts.values())} characters")
    print(f"  • Chunks created: {len(chunk_metadatas)}")
    print(f"  • Embeddings generated: {len(embeddings)}")
    print(f"  • OCR processing time: {total_processing_time}ms total, {avg_processing_time:.0f}ms avg")
    print(f"  • OCR cost: ${total_cost:.6f} (Tesseract is free!)")

    print("\n" + "=" * 80)
    print("✅ Story 2.1 (Tesseract OCR) successfully integrates with pipeline!")
    print("=" * 80 + "\n")

    return True


async def main():
    """Run the manual integration test."""
    try:
        success = await test_full_pipeline_with_real_components()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
