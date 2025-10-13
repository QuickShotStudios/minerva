#!/usr/bin/env python3
"""Test script for real Kindle screenshot text extraction."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

from PIL import Image

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from minerva.core.ingestion.embedding_generator import EmbeddingGenerator
from minerva.core.ingestion.semantic_chunking import SemanticChunker
from minerva.core.ingestion.text_extraction import TextExtractor


def find_kindle_screenshots() -> list[Path]:
    """Find all image files in screenshots directory."""
    screenshots_dir = Path("screenshots")
    if not screenshots_dir.exists():
        return []

    # Look for common image formats
    extensions = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
    screenshots = []
    for ext in extensions:
        screenshots.extend(screenshots_dir.glob(ext))

    return sorted(screenshots)


def display_image_info(image_path: Path) -> None:
    """Display information about the image."""
    try:
        img = Image.open(image_path)
        print("\n📸 Image Information:")
        print(f"  • File: {image_path.name}")
        print(f"  • Size: {img.size[0]}x{img.size[1]} pixels")
        print(f"  • Format: {img.format}")
        print(f"  • Mode: {img.mode}")
        print(f"  • File size: {image_path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"  ⚠️  Could not read image info: {e}")


async def analyze_kindle_page(screenshot_path: Path) -> dict:
    """Perform comprehensive analysis of a Kindle screenshot."""
    print("\n" + "=" * 70)
    print("KINDLE SCREENSHOT ANALYSIS")
    print("=" * 70)

    display_image_info(screenshot_path)

    # Initialize components
    extractor = TextExtractor()
    chunker = SemanticChunker(chunk_size_tokens=700, chunk_overlap_percentage=0.15)

    results = {}

    # Step 1: Text Extraction
    print("\n" + "-" * 70)
    print("STEP 1: Text Extraction with OpenAI Vision API")
    print("-" * 70)

    try:
        extracted_text, metadata = await extractor.extract_text_from_screenshot(
            screenshot_path,
            book_id="kindle-test",
            screenshot_id=str(uuid4()),
        )

        results["extraction"] = {
            "success": True,
            "text": extracted_text,
            "metadata": metadata,
        }

        print("\n✓ Text extraction successful!")
        print("\n📊 Extraction Metrics:")
        print(f"  • Characters extracted: {len(extracted_text)}")
        print(f"  • Words extracted: {len(extracted_text.split())}")
        print(f"  • Lines extracted: {len(extracted_text.splitlines())}")
        print(f"  • Tokens used: {metadata['tokens_used']}")
        print(f"  • Cost: ${metadata['cost_estimate']:.6f}")
        print(f"  • Vision model: {metadata['vision_model']}")

        # Analyze text characteristics
        has_chapter = any(
            word in extracted_text.upper()
            for word in ["CHAPTER", "SECTION", "PART"]
        )
        has_numbers = any(char.isdigit() for char in extracted_text)
        has_special = any(
            char in extracted_text for char in ["•", "–", "—", ":", ";"]
        )

        print("\n📝 Text Characteristics:")
        print(f"  • Contains chapter/section markers: {'Yes' if has_chapter else 'No'}")
        print(f"  • Contains numbers: {'Yes' if has_numbers else 'No'}")
        print(f"  • Contains special formatting: {'Yes' if has_special else 'No'}")

        # Display extracted text
        print("\n📄 Extracted Text:")
        print("=" * 70)
        print(extracted_text)
        print("=" * 70)

    except Exception as e:
        results["extraction"] = {"success": False, "error": str(e)}
        print(f"\n✗ Text extraction failed: {e}")
        return results

    # Step 2: Semantic Chunking
    print("\n" + "-" * 70)
    print("STEP 2: Semantic Chunking")
    print("-" * 70)

    try:
        screenshot_mapping = {0: uuid4()}
        chunks = await chunker.chunk_extracted_text(
            extracted_text, screenshot_mapping, book_id="kindle-test"
        )

        results["chunking"] = {
            "success": True,
            "chunks": chunks,
        }

        print("\n✓ Chunking successful!")
        print("\n📦 Chunking Results:")
        print(f"  • Total chunks: {len(chunks)}")
        print(
            f"  • Average chunk size: {sum(c.token_count for c in chunks) / len(chunks):.0f} tokens"
        )
        print(
            f"  • Min chunk size: {min(c.token_count for c in chunks)} tokens"
        )
        print(
            f"  • Max chunk size: {max(c.token_count for c in chunks)} tokens"
        )

        # Display chunk previews
        print("\n📚 Chunk Previews:")
        for i, chunk in enumerate(chunks, 1):
            print(f"\n  Chunk {i}:")
            print(f"    • Sequence: {chunk.chunk_sequence}")
            print(f"    • Tokens: {chunk.token_count}")
            print(f"    • Position: {chunk.start_position}-{chunk.end_position}")
            preview = chunk.chunk_text[:100].replace("\n", " ")
            print(f"    • Preview: {preview}...")

    except Exception as e:
        results["chunking"] = {"success": False, "error": str(e)}
        print(f"\n✗ Chunking failed: {e}")
        return results

    # Step 3: Embedding Generation
    print("\n" + "-" * 70)
    print("STEP 3: Embedding Generation")
    print("-" * 70)

    try:
        from unittest.mock import AsyncMock

        mock_session = AsyncMock()
        generator = EmbeddingGenerator(
            session=mock_session, embedding_model="text-embedding-3-small"
        )

        chunk_texts = [chunk.chunk_text for chunk in chunks]
        embeddings = await generator.generate_embeddings(
            chunk_texts, book_id="kindle-test"
        )

        results["embeddings"] = {
            "success": True,
            "count": len(embeddings),
            "dimensions": len(embeddings[0]) if embeddings else 0,
        }

        print("\n✓ Embedding generation successful!")
        print("\n🔢 Embedding Results:")
        print(f"  • Total embeddings: {len(embeddings)}")
        print(f"  • Dimensions: {len(embeddings[0])}")

        # Calculate embedding cost
        total_tokens = sum(c.token_count for c in chunks)
        embedding_cost = total_tokens * 0.02 / 1_000_000
        print(f"  • Approximate cost: ${embedding_cost:.6f}")

    except Exception as e:
        results["embeddings"] = {"success": False, "error": str(e)}
        print(f"\n✗ Embedding generation failed: {e}")
        return results

    return results


async def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("KINDLE SCREENSHOT TEXT EXTRACTION TEST")
    print("=" * 70)

    # Find screenshots
    screenshots = find_kindle_screenshots()

    if not screenshots:
        print("\n⚠️  No screenshots found in screenshots/ directory")
        print("\nPlease add a Kindle screenshot to test:")
        print("  1. Take a screenshot of a Kindle page")
        print("  2. Save it to: screenshots/kindle_page.png")
        print("  3. Run this script again")
        return

    # Display available screenshots
    print(f"\n📁 Found {len(screenshots)} screenshot(s):")
    for i, screenshot in enumerate(screenshots, 1):
        print(f"  {i}. {screenshot.name} ({screenshot.stat().st_size / 1024:.1f} KB)")

    # Select screenshot
    if len(screenshots) == 1:
        selected = screenshots[0]
        print(f"\n→ Using: {selected.name}")
    else:
        print(f"\nEnter number (1-{len(screenshots)}) or press Enter for first:")
        try:
            choice = input("> ").strip()
            if choice:
                idx = int(choice) - 1
                if 0 <= idx < len(screenshots):
                    selected = screenshots[idx]
                else:
                    print("Invalid choice, using first screenshot")
                    selected = screenshots[0]
            else:
                selected = screenshots[0]
        except (ValueError, KeyboardInterrupt):
            print("Using first screenshot")
            selected = screenshots[0]

    # Analyze the screenshot
    print(f"\n🔍 Analyzing: {selected.name}")
    print("\nThis will make real OpenAI API calls (cost: ~$0.0005)")

    results = await analyze_kindle_page(selected)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if results.get("extraction", {}).get("success"):
        extraction = results["extraction"]
        print("\n✅ Text Extraction: SUCCESS")
        print(f"   • {len(extraction['text'])} characters extracted")
        print(f"   • Cost: ${extraction['metadata']['cost_estimate']:.6f}")

    if results.get("chunking", {}).get("success"):
        chunking = results["chunking"]
        print("\n✅ Semantic Chunking: SUCCESS")
        print(f"   • {len(chunking['chunks'])} chunks created")

    if results.get("embeddings", {}).get("success"):
        embeddings = results["embeddings"]
        print("\n✅ Embedding Generation: SUCCESS")
        print(f"   • {embeddings['count']} embeddings ({embeddings['dimensions']} dims)")

    # Quality assessment prompt
    if results.get("extraction", {}).get("success"):
        print("\n" + "=" * 70)
        print("QUALITY ASSESSMENT")
        print("=" * 70)
        print("\nPlease manually review the extracted text above and rate accuracy:")
        print("  • Does it match the original Kindle page?")
        print("  • Are there any missing words or formatting issues?")
        print("  • Is the text order correct?")
        print("\nFor automated validation, see Story 2.6 (Quality Validation)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
