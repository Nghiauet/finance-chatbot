"""
Schema definitions for company data.
"""

from typing import Optional, List, Dict, Any
from datetime import date
from uuid import UUID
from pydantic import BaseModel


class CompanyBase(BaseModel):
    """Base schema for company data."""
    name: str
    ticker: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""
    pass


class CompanyResponse(CompanyBase):
    """Schema for company response."""
    id: UUID
    created_at: date

    class Config:
        orm_mode = True


class CompanyDetailResponse(CompanyResponse):
    """Schema for detailed company response."""
    financial_statements: Optional[List["FinancialStatementResponse"]] = None
    extras: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

from .financial_statement_schema import FinancialStatementResponse 