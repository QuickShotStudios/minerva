#!/usr/bin/env python3
"""Re-process existing book with UI filtering to clean up chunks."""

import asyncio
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from minerva.config import settings
from minerva.core.ingestion.text_extraction import TextExtractor
from minerva.core.ingestion.semantic_chunking import SemanticChunker
from minerva.core.ingestion.embedding_generator import EmbeddingGenerator
from minerva.db.models.book import Book
from minerva.db.models.chunk import Chunk
from minerva.db.models.screenshot import Screenshot


async def reprocess_book(book_id: str):
    """Re-process a book with UI filtering enabled."""
    # Create database engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Load book
        result = await session.execute(select(Book).where(Book.id == UUID(book_id)))
        book = result.scalar_one_or_none()

        if not book:
            print(f"Book {book_id} not found")
            return

        print(f"\n{'='*80}")
        print(f"RE-PROCESSING BOOK: {book.title}")
        print(f"{'='*80}\n")

        # Load screenshots
        result = await session.execute(
            select(Screenshot)
            .where(Screenshot.book_id == book.id)
            .order_by(Screenshot.sequence_number)
        )
        screenshots = list(result.scalars().all())
        print(f"Found {len(screenshots)} screenshots")

        # Delete existing chunks
        result = await session.execute(select(Chunk).where(Chunk.book_id == book.id))
        old_chunks = list(result.scalars().all())
        print(f"Deleting {len(old_chunks)} old chunks...")
        for chunk in old_chunks:
            await session.delete(chunk)
        await session.commit()

        # Extract text with UI filtering
        print(f"\nExtracting text with UI filtering enabled...")
        extractor = TextExtractor(filter_kindle_ui=True)
        extracted_texts = {}
        total_ui_chars_removed = 0

        for screenshot in screenshots:
            text, metadata = await extractor.extract_text_from_screenshot(
                Path(screenshot.file_path),
                book_id=str(book.id),
                screenshot_id=str(screenshot.id),
            )
            extracted_texts[screenshot.sequence_number] = text
            total_ui_chars_removed += metadata['kindle_ui_chars_removed']
            print(f"  Screenshot {screenshot.sequence_number}: {len(text)} chars (removed {metadata['kindle_ui_chars_removed']} UI chars)")

        print(f"\nTotal UI characters removed: {total_ui_chars_removed}")

        # Combine texts
        sorted_texts = sorted(extracted_texts.items())
        full_text = "\n\n".join(text for _, text in sorted_texts)

        # Create screenshot mapping
        screenshot_mapping = {}
        char_position = 0
        for seq_num, text in sorted_texts:
            screenshot_id = next(
                (s.id for s in screenshots if s.sequence_number == seq_num), None
            )
            if screenshot_id:
                screenshot_mapping[char_position] = screenshot_id
            char_position += len(text) + 2

        # Chunk text
        print(f"\nChunking text...")
        chunker = SemanticChunker()
        chunk_metadatas = await chunker.chunk_extracted_text(
            full_text, screenshot_mapping, book_id=str(book.id)
        )
        print(f"Created {len(chunk_metadatas)} chunks")

        # Generate embeddings
        print(f"\nGenerating embeddings...")
        embedding_generator = EmbeddingGenerator(session=session)
        embedding_config = await embedding_generator.get_or_create_embedding_config()

        chunk_texts = [cm.chunk_text for cm in chunk_metadatas]
        embeddings = await embedding_generator.generate_embeddings(
            chunk_texts, book_id=str(book.id)
        )

        # Create new chunks
        print(f"\nSaving chunks to database...")
        new_chunks = []
        for chunk_meta, embedding in zip(chunk_metadatas, embeddings, strict=False):
            chunk = Chunk(
                book_id=book.id,
                chunk_text=chunk_meta.chunk_text,
                chunk_sequence=chunk_meta.chunk_sequence,
                chunk_token_count=chunk_meta.token_count,
                screenshot_ids=chunk_meta.screenshot_ids,
                embedding_config_id=embedding_config.id,
                embedding=embedding,
                vision_model="tesseract",
            )
            session.add(chunk)
            new_chunks.append(chunk)

        await session.commit()

        print(f"\n{'='*80}")
        print(f"RE-PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"Book: {book.title}")
        print(f"Old chunks: {len(old_chunks)}")
        print(f"New chunks: {len(new_chunks)}")
        print(f"UI chars removed: {total_ui_chars_removed}")
        print(f"{'='*80}\n")

        # Show sample of cleaned chunk
        if new_chunks:
            print("Sample of first cleaned chunk:")
            print("-" * 80)
            print(new_chunks[0].chunk_text[:500])
            print("-" * 80)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python reprocess_with_filtering.py <book_id>")
        sys.exit(1)

    book_id = sys.argv[1]
    asyncio.run(reprocess_book(book_id))
