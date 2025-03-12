"""SQLAlchemy ORM model for the CompanyExtra entity."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base


class CompanyExtra(Base):
    __tablename__ = 'company_extras'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    category = Column(String(100), nullable=False)  # e.g., dividend, board_of_directors, ownership
    data = Column(JSONB, nullable=False)  # flexible JSON data
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship('Company', back_populates='company_extras')

    # Unique constraint to prevent duplicate categories
    __table_args__ = (
        UniqueConstraint('company_id', 'category', name='uix_company_extra_category'),
    ) 