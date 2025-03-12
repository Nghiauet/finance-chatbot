"""
Schema definitions for financial statements.
"""

from typing import List, Dict, Any, Optional
from datetime import date
from enum import Enum
from uuid import UUID
from pydantic import BaseModel


class StatementTypeEnum(str, Enum):
    """Enum for financial statement types."""
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"


class FinancialMetricSchema(BaseModel):
    """Schema for financial metric."""
    metric_name: str
    metric_value: float


class FinancialNoteSchema(BaseModel):
    """Schema for financial note."""
    note: str


class FinancialStatementBase(BaseModel):
    """Base schema for financial statement."""
    statement_type: StatementTypeEnum
    fiscal_year: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    period_type: Optional[str] = None


class FinancialStatementCreate(FinancialStatementBase):
    """Schema for creating a financial statement."""
    metrics: Dict[str, float]
    notes: Optional[List[str]] = None


class FinancialStatementUpdate(BaseModel):
    """Schema for updating a financial statement."""
    fiscal_year: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    period_type: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    notes: Optional[List[str]] = None


class FinancialStatementResponse(FinancialStatementBase):
    """Schema for financial statement response."""
    id: UUID
    metrics: List[FinancialMetricSchema]
    notes: List[FinancialNoteSchema]
    created_at: date

    class Config:
        orm_mode = True 