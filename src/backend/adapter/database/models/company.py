# adapter/database/models/company.py
"""SQLAlchemy ORM model for the Company entity."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Company(Base):
    __tablename__ = 'companies'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    ticker = Column(String(50), unique=True)
    industry = Column(String(100))
    country = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    financial_statements = relationship('FinancialStatement', back_populates='company', cascade="all, delete-orphan")
    company_extras = relationship('CompanyExtra', back_populates='company', cascade="all, delete-orphan")