"""EmbeddingConfig model for tracking embedding models used."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class EmbeddingConfig(SQLModel, table=True):
    """EmbeddingConfig model representing an embedding model configuration."""

    __tablename__ = "embedding_configs"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
    )
    model_name: str = Field(nullable=False, index=True)
    model_version: str = Field(nullable=False)
    dimensions: int = Field(nullable=False)
    is_active: bool = Field(default=True, nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
