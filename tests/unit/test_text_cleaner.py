"""Unit tests for text cleaner functionality."""

import pytest

from minerva.core.ingestion.text_cleaner import TextCleaner


class TestTextCleaner:
    """Test suite for TextCleaner class."""

    @pytest.fixture
    def cleaner(self) -> TextCleaner:
        """Create TextCleaner instance for testing."""
        return TextCleaner()

    def test_remove_page_numbers(self, cleaner: TextCleaner) -> None:
        """Test removal of page number indicators."""
        text = "Page 10 of 200 » 5%\n\nActual book content here."
        cleaned = cleaner.clean(text)
        assert "Page 10 of 200" not in cleaned
        assert "5%" not in cleaned
        assert "Actual book content here." in cleaned

    def test_remove_roman_numeral_pages(self, cleaner: TextCleaner) -> None:
        """Test removal of page numbers with roman numerals."""
        text = "Page xi of 209 » 4%\n\nBook introduction text."
        cleaned = cleaner.clean(text)
        assert "Page xi of 209" not in cleaned
        assert "Book introduction text." in cleaned

    def test_remove_kindle_library_text(self, cleaner: TextCleaner) -> None:
        """Test removal of Kindle Library navigation text."""
        text = "Kindle Library\n\nChapter One\n\nThe story begins..."
        cleaned = cleaner.clean(text)
        assert "Kindle Library" not in cleaned
        assert "Chapter One" in cleaned
        assert "The story begins..." in cleaned

    def test_remove_reading_speed_indicators(self, cleaner: TextCleaner) -> None:
        """Test removal of reading speed learning indicators."""
        text = "Learning reading speed, +\n\nChapter content here."
        cleaned = cleaner.clean(text)
        assert "Learning reading speed" not in cleaned
        assert "Chapter content here." in cleaned

    def test_remove_location_indicators(self, cleaner: TextCleaner) -> None:
        """Test removal of location indicators."""
        text = "Location 2 of 2771 « 0%\n\nChapter content here."
        cleaned = cleaner.clean(text)
        assert "Location 2 of 2771" not in cleaned
        assert "« 0%" not in cleaned
        assert "Chapter content here." in cleaned

    def test_preserve_book_content(self, cleaner: TextCleaner) -> None:
        """Test that actual book content is preserved."""
        text = """Page 50 of 300 » 16%

        Chapter 3: The Journey Begins

        Once upon a time, in a land far away, there lived a brave knight.
        The knight's name was Sir Galahad, and he was known throughout
        the kingdom for his courage and honor.

        Page 51 of 300 » 17%"""

        cleaned = cleaner.clean(text)

        # Check that UI elements are removed
        assert "Page 50 of 300" not in cleaned
        assert "Page 51 of 300" not in cleaned
        assert "16%" not in cleaned
        assert "17%" not in cleaned

        # Check that content is preserved
        assert "Chapter 3: The Journey Begins" in cleaned
        assert "Once upon a time, in a land far away" in cleaned
        assert "Sir Galahad" in cleaned
        assert "courage and honor" in cleaned

    def test_multiple_patterns_in_one_text(self, cleaner: TextCleaner) -> None:
        """Test removal of multiple UI patterns in one text block."""
        text = """Page x of 209 » 39% KA ey W Kindle Library Learning reading speed,+

        If you've ever had the crazy dream to start
        your own business,
        If you've ever dreamed of doing your own thing,

        Page xi of 209 » 4%"""

        cleaned = cleaner.clean(text)

        # Check all UI elements are removed
        assert "Page x of 209" not in cleaned
        assert "Page xi of 209" not in cleaned
        assert "39%" not in cleaned
        assert "4%" not in cleaned
        assert "Kindle Library" not in cleaned
        assert "Learning reading speed" not in cleaned

        # Check content is preserved
        assert "If you've ever had the crazy dream" in cleaned
        assert "your own business" in cleaned

    def test_whitespace_normalization(self, cleaner: TextCleaner) -> None:
        """Test that excessive whitespace is normalized."""
        text = """Content line 1





        Content line 2"""

        cleaned = cleaner.clean(text)

        # Should have content but normalized whitespace
        assert "Content line 1" in cleaned
        assert "Content line 2" in cleaned
        # Should not have more than 2 consecutive blank lines
        assert "\n\n\n\n" not in cleaned

    def test_empty_text_handling(self, cleaner: TextCleaner) -> None:
        """Test handling of empty or whitespace-only text."""
        assert cleaner.clean("") == ""
        assert cleaner.clean("   ") == ""
        assert cleaner.clean("\n\n\n") == ""

    def test_custom_patterns(self) -> None:
        """Test adding custom filtering patterns."""
        custom_cleaner = TextCleaner(custom_patterns=[r"CUSTOM_PATTERN"])
        text = "CUSTOM_PATTERN should be removed\n\nBut this stays."
        cleaned = custom_cleaner.clean(text)
        assert "CUSTOM_PATTERN" not in cleaned
        assert "But this stays." in cleaned

    def test_aggressive_cleaning(self, cleaner: TextCleaner) -> None:
        """Test aggressive cleaning mode."""
        text = """Actual content here.
        1
        x
        More content.
        42
        Final content."""

        cleaned = cleaner.clean(text, aggressive=True)

        # Aggressive mode should remove very short lines
        assert "Actual content here." in cleaned
        assert "More content." in cleaned
        assert "Final content." in cleaned
        # Short lines should be removed
        lines = cleaned.split("\n")
        for line in lines:
            if line.strip():  # Non-empty lines
                assert len(line.strip()) >= 3 or line.strip() == ""

    def test_statistics_calculation(self, cleaner: TextCleaner) -> None:
        """Test statistics calculation for cleaning operation."""
        original = "Page 10 of 200 » 5%\n\nActual content here."
        cleaned = cleaner.clean(original)
        stats = cleaner.get_statistics(original, cleaned)

        assert stats["original_chars"] == len(original)
        assert stats["cleaned_chars"] == len(cleaned)
        assert stats["chars_removed"] > 0
        assert stats["removal_percentage"] > 0
        assert "original_lines" in stats
        assert "cleaned_lines" in stats

    def test_case_insensitive_matching(self, cleaner: TextCleaner) -> None:
        """Test that pattern matching is case-insensitive."""
        text_lower = "page 10 of 200 » 5%\n\nContent."
        text_upper = "PAGE 10 OF 200 » 5%\n\nContent."
        text_mixed = "PaGe 10 oF 200 » 5%\n\nContent."

        cleaned_lower = cleaner.clean(text_lower)
        cleaned_upper = cleaner.clean(text_upper)
        cleaned_mixed = cleaner.clean(text_mixed)

        # All should have page indicators removed
        assert "page 10" not in cleaned_lower.lower()
        assert "page 10" not in cleaned_upper.lower()
        assert "page 10" not in cleaned_mixed.lower()

        # Content should be preserved in all
        assert "Content." in cleaned_lower
        assert "Content." in cleaned_upper
        assert "Content." in cleaned_mixed

    def test_preserve_legitimate_percentages(self, cleaner: TextCleaner) -> None:
        """Test that legitimate percentages in book content are preserved."""
        # Progress percentages with symbols should be removed
        text_ui = "Content here. » 39% Next content."
        cleaned_ui = cleaner.clean(text_ui)
        assert "39%" not in cleaned_ui

        # But percentages that are part of content should stay
        # (This test verifies our patterns are specific enough)
        text_content = "The study showed a 95% success rate in patients."
        cleaned_content = cleaner.clean(text_content)
        assert "95%" in cleaned_content

    def test_real_world_example(self, cleaner: TextCleaner) -> None:
        """Test with real-world Kindle OCR output."""
        text = """Subjects: LCSH: New business enterprises. | Business planning. | Strategic planning. | Entrepreneurship. Classification: LCC HD62.5 .L4767 2019 | DDC 658.1/1--de23 LC record available at ht tps://Iccn.loc.gov/2019000163 Hardcover ISBN: 978-1-4019-5747-6 e-book ISBN: 978-1-4019-5748-3 Audiobook ISBN: 978-1-4019-5749-0 10987654321 1st edition, April 2019 Printed in the United States of America Page x of 209 » 39% KA ey W Kindle Library Learning reading speed,+

If you've ever had the crazy dream to start

your own business,
If you've ever dreamed of doing your own thing,
If you've ever failed, or lost it all on something ...
In a quest to shake the status quo,

If you have something right now that is

changing the world...

CHOOSE

Page xi of 209 » 4%

But you don't know where to take it next."""

        cleaned = cleaner.clean(text)

        # UI elements should be removed
        assert "Page x of 209" not in cleaned
        assert "Page xi of 209" not in cleaned
        assert "Kindle Library" not in cleaned
        assert "Learning reading speed" not in cleaned

        # Book content should be preserved
        assert "If you've ever had the crazy dream" in cleaned
        assert "your own business" in cleaned
        assert "CHOOSE" in cleaned
        assert "But you don't know where to take it next" in cleaned

        # ISBN and publication info should be preserved (it's book metadata)
        assert "ISBN" in cleaned
        assert "Printed in the United States" in cleaned
