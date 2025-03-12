"""SQLAlchemy ORM model for the FinancialStatement entity."""

import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, ForeignKey, DateTime, Date, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class FinancialStatement(Base):
    __tablename__ = 'financial_statements'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    statement_type = Column(Enum('income_statement', 'balance_sheet', 'cash_flow', name='statement_types'), nullable=False)
    fiscal_year = Column(String(10), nullable=False)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    period_type = Column(String(50), nullable=True)  # e.g., KT/HN, CKT/HN
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship('Company', back_populates='financial_statements')
    metrics = relationship('FinancialMetric', back_populates='statement', cascade="all, delete-orphan")
    notes = relationship('FinancialNote', back_populates='statement', cascade="all, delete-orphan")

    # Unique constraint to prevent duplicate statements
    __table_args__ = (
        UniqueConstraint('company_id', 'statement_type', 'fiscal_year', name='uix_financial_statement'),
    ) 