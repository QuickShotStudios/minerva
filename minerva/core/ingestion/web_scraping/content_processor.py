"""Content processing - deduplication and preparation for embedding."""

import hashlib
import logging
from typing import Dict, List

from datasketch import MinHash, MinHashLSH

from minerva.core.ingestion.web_scraping.content_extractor import ExtractedContent

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Process extracted content: deduplicate, prepare for chunking.

    Implements two-level deduplication:
    1. Page-level: Exact duplicate detection using SHA256
    2. Chunk-level: Fuzzy duplicate detection using MinHash LSH
    """

    def __init__(self, similarity_threshold: float = 0.95):
        """Initialize content processor.

        Args:
            similarity_threshold: Threshold for fuzzy deduplication (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold

    def deduplicate_pages(self, pages: List[ExtractedContent]) -> List[ExtractedContent]:
        """Remove exact duplicate pages using SHA256 hash.

        Args:
            pages: List of extracted content from pages

        Returns:
            List of unique pages (duplicates removed)
        """
        seen_hashes = set()
        unique_pages = []

        for page in pages:
            # Hash the text content
            content_hash = hashlib.sha256(page.text.encode("utf-8")).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_pages.append(page)
            else:
                logger.debug(f"Skipping duplicate page: {page.url}")

        duplicates_removed = len(pages) - len(unique_pages)
        if duplicates_removed > 0:
            logger.info(
                f"Page deduplication: {len(pages)} → {len(unique_pages)} "
                f"({duplicates_removed} duplicates removed)"
            )

        return unique_pages

    def deduplicate_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Remove near-duplicate chunks using MinHash LSH.

        Args:
            chunks: List of chunk dictionaries with 'text' and 'id' fields

        Returns:
            List of unique chunks (near-duplicates removed)
        """
        if not chunks:
            return chunks

        logger.info(f"Starting chunk deduplication on {len(chunks)} chunks")

        # Create LSH index
        lsh = MinHashLSH(threshold=self.similarity_threshold, num_perm=128)
        unique_chunks = []
        chunk_hashes: Dict[str, MinHash] = {}

        for chunk in chunks:
            chunk_id = chunk.get("id", str(len(unique_chunks)))
            chunk_text = chunk.get("text", "")

            if not chunk_text:
                continue

            # Create MinHash for this chunk
            minhash = MinHash(num_perm=128)
            for word in chunk_text.split():
                minhash.update(word.encode("utf-8"))

            # Check if similar chunk exists
            similar_chunks = lsh.query(minhash)

            if not similar_chunks:
                # No similar chunks found, add to unique list
                lsh.insert(chunk_id, minhash)
                chunk_hashes[chunk_id] = minhash
                unique_chunks.append(chunk)
            else:
                logger.debug(f"Skipping near-duplicate chunk: {chunk_id}")

        duplicates_removed = len(chunks) - len(unique_chunks)
        if duplicates_removed > 0:
            logger.info(
                f"Chunk deduplication: {len(chunks)} → {len(unique_chunks)} "
                f"({duplicates_removed} near-duplicates removed, "
                f"threshold={self.similarity_threshold})"
            )

        return unique_chunks

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using MinHash.

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Create MinHash for both texts
        mh1 = MinHash(num_perm=128)
        mh2 = MinHash(num_perm=128)

        for word in text1.split():
            mh1.update(word.encode("utf-8"))

        for word in text2.split():
            mh2.update(word.encode("utf-8"))

        # Calculate Jaccard similarity
        return mh1.jaccard(mh2)
