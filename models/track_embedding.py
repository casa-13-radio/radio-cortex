# models/track_embedding.py
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, VECTOR
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from models.database import Base

class TrackEmbedding(Base):
    __tablename__ = "track_embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(UUID(as_uuid=True), ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False)
    embedding = Column(VECTOR(384))  # Dimensão para all-MiniLM-L6-v2
    model_version = Column(String(50), nullable=False, default="all-MiniLM-L6-v2")
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento
    track = relationship("Track", back_populates="embeddings")