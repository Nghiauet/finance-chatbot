"""Service for financial analysis business logic."""

import uuid
from typing import List, Dict, Any, Optional

from domain.models import StatementType
from domain.services.financial_statement_service import FinancialStatementService


class FinancialAnalysisService:
    """Service for financial analysis business logic."""
    
    def __init__(self, statement_service: FinancialStatementService):
        self.statement_service = statement_service
    
    async def calculate_financial_ratios(
        self,
        company_id: uuid.UUID,
        fiscal_year: str
    ) -> Dict[str, float]:
        """Calculate financial ratios for a company for a specific fiscal year."""
        income_statement = await self.statement_service.get_financial_statement_by_type(
            company_id, StatementType.INCOME_STATEMENT, fiscal_year
        )
        
        balance_sheet = await self.statement_service.get_financial_statement_by_type(
            company_id, StatementType.BALANCE_SHEET, fiscal_year
        )
        
        cash_flow = await self.statement_service.get_financial_statement_by_type(
            company_id, StatementType.CASH_FLOW, fiscal_year
        )
        
        if not income_statement or not balance_sheet:
            raise ValueError(f"Income statement or balance sheet missing for {fiscal_year}")
        
        # Convert metrics to dictionaries for easier access
        income_metrics = {m.metric_name: m.metric_value for m in income_statement.metrics}
        balance_metrics = {m.metric_name: m.metric_value for m in balance_sheet.metrics}
        cash_metrics = {}
        if cash_flow:
            cash_metrics = {m.metric_name: m.metric_value for m in cash_flow.metrics}
        
        # Calculate ratios (example calculations, adjust based on your actual metrics)
        ratios = {}
        
        # Profitability ratios
        if 'revenue' in income_metrics and 'net_income' in income_metrics:
            ratios['net_profit_margin'] = (income_metrics['net_income'] / income_metrics['revenue']) * 100
        
        # Liquidity ratios
        if 'current_assets' in balance_metrics and 'current_liabilities' in balance_metrics:
            if balance_metrics['current_liabilities'] != 0:
                ratios['current_ratio'] = balance_metrics['current_assets'] / balance_metrics['current_liabilities']
        
        # Solvency ratios
        if 'total_assets' in balance_metrics and 'total_liabilities' in balance_metrics:
            if balance_metrics['total_assets'] != 0:
                ratios['debt_to_assets'] = (balance_metrics['total_liabilities'] / balance_metrics['total_assets']) * 100
        
        # Return on Investment ratios
        if 'net_income' in income_metrics and 'total_assets' in balance_metrics:
            if balance_metrics['total_assets'] != 0:
                ratios['return_on_assets'] = (income_metrics['net_income'] / balance_metrics['total_assets']) * 100
        
        if 'net_income' in income_metrics and 'total_equity' in balance_metrics:
            if balance_metrics['total_equity'] != 0:
                ratios['return_on_equity'] = (income_metrics['net_income'] / balance_metrics['total_equity']) * 100
        
        # Efficiency ratios
        if 'revenue' in income_metrics and 'total_assets' in balance_metrics:
            if balance_metrics['total_assets'] != 0:
                ratios['asset_turnover'] = income_metrics['revenue'] / balance_metrics['total_assets']
        
        # Cash flow ratios
        if cash_flow and 'operating_cash_flow' in cash_metrics and 'total_liabilities' in balance_metrics:
            if balance_metrics['total_liabilities'] != 0:
                ratios['cash_flow_to_debt'] = cash_metrics['operating_cash_flow'] / balance_metrics['total_liabilities']
        
        return ratios
    
    async def compare_companies_metric(
        self,
        company_ids: List[uuid.UUID],
        metric_name: str,
        statement_type: StatementType,
        fiscal_year: str
    ) -> Dict[uuid.UUID, Optional[float]]:
        """Compare a specific metric across multiple companies."""
        result = {}
        
        for company_id in company_ids:
            value = await self.statement_service.get_financial_metric(
                company_id, metric_name, statement_type, fiscal_year
            )
            result[company_id] = value
        
        return result
    
    async def calculate_trend_analysis(
        self,
        company_id: uuid.UUID,
        metric_name: str,
        statement_type: StatementType,
        fiscal_years: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate trend analysis for a specific metric over multiple years."""
        values = await self.statement_service.compare_financial_metrics(
            company_id, metric_name, statement_type, fiscal_years
        )
        
        # Skip years with missing data
        filtered_values = {year: value for year, value in values.items() if value is not None}
        
        if len(filtered_values) < 2:
            return {"values": filtered_values, "growth_rates": {}}
        
        # Calculate year-over-year growth rates
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
            "values": filtered_values,
            "growth_rates": growth_rates
        }
    
    async def calculate_industry_comparison(
        self,
        company_id: uuid.UUID,
        industry: str,
        metric_name: str,
        statement_type: StatementType,
        fiscal_year: str
    ) -> Dict[str, Any]:
        """
        Compare a company's metric with industry average.
        This is a placeholder implementation - you would need a way to get industry data.
        """
        # This would require additional repository methods to get companies by industry
        # and calculate industry averages. For now, just return the company's metric.
        company_metric = await self.statement_service.get_financial_metric(
            company_id, metric_name, statement_type, fiscal_year
        )
        
        # Placeholder for industry average
        industry_average = None
        
        return {
            "company_value": company_metric,
            "industry_average": industry_average,
            "difference": None if industry_average is None or company_metric is None else company_metric - industry_average
        } 