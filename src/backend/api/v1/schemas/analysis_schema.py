"""
Schema definitions for financial analysis requests and responses.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel

from .financial_statement_schema import StatementTypeEnum


class MetricComparisonRequest(BaseModel):
    """Schema for metric comparison request."""
    metric_name: str
    statement_type: StatementTypeEnum
    fiscal_years: List[str]


class MetricComparisonResponse(BaseModel):
    """Schema for metric comparison response."""
    values: Dict[str, Optional[float]]
    growth_rates: Dict[str, float]


class FinancialRatiosResponse(BaseModel):
    """Schema for financial ratios response."""
    ratios: Dict[str, float]
    fiscal_year: str


class CompanyComparisonRequest(BaseModel):
    """Schema for company comparison request."""
    company_ids: List[UUID]
    metric_name: str
    statement_type: StatementTypeEnum
    fiscal_year: str


class CompanyComparisonResponse(BaseModel):
    """Schema for company comparison response."""
    values: Dict[str, Optional[float]]


class TrendAnalysisRequest(BaseModel):
    """Schema for trend analysis request."""
    metric_name: str
    statement_type: StatementTypeEnum
    fiscal_years: List[str]


class TrendAnalysisResponse(BaseModel):
    """Schema for trend analysis response."""
    values: Dict[str, float]
    growth_rates: Dict[str, float] 