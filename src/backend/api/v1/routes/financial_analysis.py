"""
API routes for financial analysis endpoints.
"""

from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from domain.services import FinancialAnalysisService
from domain.models import StatementType
from api.v1.schemas.financial_analysis_schema import (
    MetricComparisonRequest,
    MetricComparisonResponse,
    FinancialRatiosResponse,
    CompanyComparisonRequest,
    CompanyComparisonResponse,
    TrendAnalysisRequest,
    TrendAnalysisResponse,
    StatementTypeEnum
)
from api.v1.deps import get_financial_analysis_service

router = APIRouter(prefix="/financial-analysis", tags=["financial analysis"])


@router.get("/{company_id}/ratios/{fiscal_year}", response_model=FinancialRatiosResponse)
async def calculate_financial_ratios(
    company_id: UUID,
    fiscal_year: str,
    analysis_service: FinancialAnalysisService = Depends(get_financial_analysis_service)
):
    """Calculate financial ratios for a company for a specific fiscal year."""
    try:
        ratios = await analysis_service.calculate_financial_ratios(
            company_id=company_id,
            fiscal_year=fiscal_year
        )
        return {
            "ratios": ratios,
            "fiscal_year": fiscal_year
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{company_id}/metric-comparison", response_model=MetricComparisonResponse)
async def compare_financial_metrics(
    company_id: UUID,
    comparison_data: MetricComparisonRequest,
    analysis_service: FinancialAnalysisService = Depends(get_financial_analysis_service)
):
    """Compare a financial metric across multiple fiscal years."""
    values = await analysis_service.statement_service.compare_financial_metrics(
        company_id=company_id,
        metric_name=comparison_data.metric_name,
        statement_type=StatementType(comparison_data.statement_type.value),
        fiscal_years=comparison_data.fiscal_years
    )
    
    # Calculate growth rates for years with data
    filtered_values = {year: value for year, value in values.items() if value is not None}
    sorted_years = sorted(filtered_values.keys())
    growth_rates = {}
    
    for i in range(1, len(sorted_years)):
        current_year = sorted_years[i]
        previous_year = sorted_years[i-1]
        
        current_value = filtered_values[current_year]
        previous_value = filtered_values[previous_year]
        
        if previous_value != 0:
            growth_rate = ((current_value - previous_value) / previous_value) * 100
            growth_rates[f"{previous_year}_to_{current_year}"] = growth_rate
    
    return {
        "values": values,
        "growth_rates": growth_rates
    }


@router.post("/company-comparison", response_model=CompanyComparisonResponse)
async def compare_companies(
    comparison_data: CompanyComparisonRequest,
    analysis_service: FinancialAnalysisService = Depends(get_financial_analysis_service)
):
    """Compare a specific metric across multiple companies."""
    values = await analysis_service.compare_companies_metric(
        company_ids=comparison_data.company_ids,
        metric_name=comparison_data.metric_name,
        statement_type=StatementType(comparison_data.statement_type.value),
        fiscal_year=comparison_data.fiscal_year
    )
    
    # Convert UUID keys to strings for JSON response
    string_values = {str(company_id): value for company_id, value in values.items()}
    
    return {
        "values": string_values
    }


@router.post("/{company_id}/trend-analysis", response_model=TrendAnalysisResponse)
async def analyze_trend(
    company_id: UUID,
    trend_data: TrendAnalysisRequest,
    analysis_service: FinancialAnalysisService = Depends(get_financial_analysis_service)
):
    """Calculate trend analysis for a specific metric over multiple years."""
    result = await analysis_service.calculate_trend_analysis(
        company_id=company_id,
        metric_name=trend_data.metric_name,
        statement_type=StatementType(trend_data.statement_type.value),
        fiscal_years=trend_data.fiscal_years
    )
    
    return result 