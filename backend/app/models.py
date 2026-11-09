from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from pgvector.sqlalchemy import VECTOR

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    filename = Column(
        String(255),
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    # Unique SHA-256 hash of extracted document content
    content_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chunk_number = Column(
        Integer,
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    # Amazon Titan Text Embeddings V2 - 1024 dimensions
    embedding = Column(
        VECTOR(1024),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )