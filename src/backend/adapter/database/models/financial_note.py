"""SQLAlchemy ORM model for the FinancialNote entity."""

import uuid
from datetime import datetime

from sqlalchemy import Column, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class FinancialNote(Base):
    __tablename__ = 'financial_notes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey('financial_statements.id'), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    statement = relationship('FinancialStatement', back_populates='notes') 