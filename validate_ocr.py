#!/usr/bin/env python3
"""Manual validation script for Story 2.1 AC 11.

Tests Tesseract OCR extraction on 5 diverse book screenshots
and displays results for visual validation.
"""

import asyncio
import sys
from pathlib import Path

from minerva.core.ingestion.text_extraction import TextExtractor


async def validate_screenshot(extractor: TextExtractor, screenshot_path: Path, index: int):
    """Extract text from a screenshot and display results."""
    print(f"\n{'='*80}")
    print(f"SCREENSHOT {index}: {screenshot_path.name}")
    print(f"{'='*80}")

    try:
        # Extract text
        text, metadata = await extractor.extract_text_from_screenshot(
            screenshot_path,
            book_id="validation-test",
            screenshot_id=f"screenshot-{index}"
        )

        # Display metadata
        print("\n📊 METADATA:")
        print(f"  OCR Method: {metadata['ocr_method']}")
        print(f"  Tesseract Version: {metadata['tesseract_version']}")
        print(f"  Processing Time: {metadata['processing_time_ms']}ms")
        print(f"  Text Length: {len(text)} characters")
        print(f"  AI Formatting: {metadata['use_ai_formatting']}")
        print(f"  Cost: ${metadata['cost_estimate']:.6f}")

        # Display extracted text
        print("\n📄 EXTRACTED TEXT:")
        print("-" * 80)
        print(text)
        print("-" * 80)

        # Validation checks
        print("\n✅ VALIDATION CHECKS:")
        has_content = len(text.strip()) > 0
        has_paragraphs = "\n\n" in text or "\n" in text
        avg_word_length = sum(len(word) for word in text.split()) / max(len(text.split()), 1)
        reasonable_words = 2 <= avg_word_length <= 12

        print(f"  ✓ Has content: {has_content}")
        print(f"  ✓ Has paragraph breaks: {has_paragraphs}")
        print(f"  ✓ Reasonable word length (2-12 avg): {reasonable_words} (avg: {avg_word_length:.1f})")
        print(f"  ✓ Processing time under 5s: {metadata['processing_time_ms'] < 5000}")

        return {
            "screenshot": screenshot_path.name,
            "success": True,
            "text_length": len(text),
            "processing_time_ms": metadata['processing_time_ms'],
            "has_structure": has_paragraphs,
        }

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return {
            "screenshot": screenshot_path.name,
            "success": False,
            "error": str(e),
        }


async def main():
    """Run validation on all screenshots."""
    print("="*80)
    print("TESSERACT OCR MANUAL VALIDATION - Story 2.1 AC 11")
    print("="*80)

    # Get screenshots
    screenshots_dir = Path("screenshots")
    screenshots = sorted(screenshots_dir.glob("Kindle-*.png"))[:5]  # Take first 5

    if len(screenshots) < 5:
        print(f"\n⚠️  WARNING: Only found {len(screenshots)} screenshots (need 5)")
        print("Available screenshots:")
        for s in screenshots:
            print(f"  - {s.name}")
        print("\nProceeding with available screenshots...\n")

    # Initialize extractor (without AI formatting for faster validation)
    print("\n🔧 Initializing TextExtractor (AI formatting disabled for speed)...")
    extractor = TextExtractor(use_ai_formatting=False)
    print("✓ TextExtractor ready\n")

    # Validate each screenshot
    results = []
    for i, screenshot in enumerate(screenshots, 1):
        result = await validate_screenshot(extractor, screenshot, i)
        results.append(result)

    # Summary
    print(f"\n\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")

    successful = sum(1 for r in results if r.get("success", False))
    print(f"\nTotal Screenshots Tested: {len(results)}")
    print(f"Successful Extractions: {successful}/{len(results)}")

    if successful == len(results):
        print("\n✅ ALL EXTRACTIONS SUCCESSFUL!")
    else:
        print(f"\n⚠️  {len(results) - successful} extraction(s) failed")

    print("\nPer-Screenshot Results:")
    for r in results:
        if r.get("success"):
            print(f"  ✓ {r['screenshot']}: {r['text_length']} chars, {r['processing_time_ms']}ms, structure={r['has_structure']}")
        else:
            print(f"  ✗ {r['screenshot']}: {r.get('error', 'Unknown error')}")

    avg_time = sum(r.get('processing_time_ms', 0) for r in results if r.get('success')) / max(successful, 1)
    print(f"\nAverage Processing Time: {avg_time:.0f}ms ({avg_time/1000:.2f}s)")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Review the extracted text above for accuracy")
    print("2. Verify structure preservation (paragraphs, lists, headers)")
    print("3. Estimate accuracy percentage based on visual comparison")
    print("4. Document findings in Story 2.1 manual validation task")
    print("="*80)

    return 0 if successful == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
