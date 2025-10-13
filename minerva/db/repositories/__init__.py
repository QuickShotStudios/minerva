"""Database repositories for Minerva."""

from minerva.db.repositories.base_repository import BaseRepository
from minerva.db.repositories.book_repository import BookRepository
from minerva.db.repositories.screenshot_repository import ScreenshotRepository

__all__ = [
    "BaseRepository",
    "BookRepository",
    "ScreenshotRepository",
]
