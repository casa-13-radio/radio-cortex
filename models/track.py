"""
Track model for music tracks.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base


class Track(Base):
    """Music track."""
    
    __tablename__ = "tracks"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    artist_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artists.id"),
        nullable=False,
        index=True
    )
    album: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    license_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("licenses.id"),
        nullable=False,
        index=True
    )
    
    # Audio
    audio_url: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    bitrate_kbps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    format: Mapped[str] = mapped_column(String(10), default="mp3")
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Classification (by Librarian Agent)
    primary_genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    secondary_genres: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String),
        nullable=True
    )
    mood_tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String),
        nullable=True
    )
    cultural_context: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Technical metadata
    id3_tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    audio_fingerprint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Embeddings (for semantic search)
    embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(384),  # sentence-transformers dimension
        nullable=True
    )
    
    # Source tracking
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    collected_by: Mapped[str] = mapped_column(
        String(50),
        default="hunter_agent",
        nullable=False
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    # Workflow status
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending_enrichment",
        nullable=False,
        index=True
    )
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_enrichment', 'pending_compliance', 'approved', 'rejected', 'on_hold')",
            name="valid_status"
        ),
        CheckConstraint(
            "duration_seconds > 0",
            name="positive_duration"
        ),
    )
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    artist: Mapped["Artist"] = relationship(
        "Artist",
        back_populates="tracks"
    )
    license: Mapped["License"] = relationship(
        "License",
        back_populates="tracks"
    )
    
    def __repr__(self) -> str:
        return f"<Track {self.title} by {self.artist.name if self.artist else 'Unknown'}>"