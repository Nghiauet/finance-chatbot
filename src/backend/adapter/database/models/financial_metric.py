"""SQLAlchemy ORM model for the FinancialMetric entity."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class FinancialMetric(Base):
    __tablename__ = 'financial_metrics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey('financial_statements.id'), nullable=False)
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    statement = relationship('FinancialStatement', back_populates='metrics')

    # Unique constraint to prevent duplicate metrics
    __table_args__ = (
        UniqueConstraint('statement_id', 'metric_name', name='uix_financial_metric'),
    ) 