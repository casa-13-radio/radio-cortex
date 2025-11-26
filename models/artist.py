# models/artist.py - CORRIGIDO
from sqlalchemy import Column, String, Text, ARRAY, Integer, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import uuid

from models.database import Base

class Artist(Base):
    __tablename__ = "artists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    name_normalized = Column(String(300))
    aliases = Column(ARRAY(String))
    bio = Column(Text)
    style = Column(String(200))
    country = Column(String(2))
    website_url = Column(Text)
    social_links = Column(JSONB)
    artist_metadata = Column(JSONB)
    track_count = Column(Integer, default=0)
    total_plays = Column(BigInteger, default=0)

    tracks = relationship("Track", back_populates="artist")