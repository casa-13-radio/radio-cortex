# models/license.py
from sqlalchemy import Column, String, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from models.database import Base

class License(Base):
    __tablename__ = "licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_code = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(200), nullable=False)
    url = Column(Text, nullable=False)
    allows_commercial = Column(Boolean, nullable=False)
    allows_derivatives = Column(Boolean, nullable=False)
    requires_attribution = Column(Boolean, nullable=False)
    requires_share_alike = Column(Boolean, nullable=False)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    icon_url = Column(Text)
    description = Column(Text)

    # Relacionamento com tracks
    tracks = relationship("Track", back_populates="license")