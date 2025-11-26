# models/track.py
from sqlalchemy import Column, String, Text, Integer, BigInteger, DateTime, Boolean, ARRAY, JSONB, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from models.database import Base

class Track(Base):
    __tablename__ = "tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    artist_id = Column(UUID(as_uuid=True), nullable=False)
    album = Column(String(500))
    license_id = Column(UUID(as_uuid=True), nullable=False)
    audio_url = Column(Text, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    bitrate_kbps = Column(Integer)
    format = Column(String(10), default='mp3')
    file_size_bytes = Column(BigInteger)
    primary_genre = Column(String(100))
    secondary_genres = Column(ARRAY(String))
    mood_tags = Column(ARRAY(String))
    cultural_context = Column(String(200))
    id3_tags = Column(JSONB)
    audio_fingerprint = Column(Text)
    source_url = Column(Text, nullable=False)
    collected_by = Column(String(50), default='hunter_agent')
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default='pending_enrichment')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relacionamentos
    artist = relationship("Artist", back_populates="tracks")
    license = relationship("License", back_populates="tracks")
    embeddings = relationship("TrackEmbedding", back_populates="track", cascade="all, delete-orphan")

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