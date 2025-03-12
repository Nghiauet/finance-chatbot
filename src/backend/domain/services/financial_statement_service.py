"""Service for financial statement related business logic."""

import uuid
from typing import List, Dict, Optional
from datetime import date

from domain.models import FinancialStatement, FinancialMetric, FinancialNote, StatementType
from domain.repositories import FinancialStatementRepository, CompanyRepository


class FinancialStatementService:
    """Service for financial statement related business logic."""
    
    def __init__(
        self, 
        statement_repo: FinancialStatementRepository,
        company_repo: CompanyRepository
    ):
        self.statement_repo = statement_repo
        self.company_repo = company_repo
    
    async def create_financial_statement(
        self,
        company_id: uuid.UUID,
        statement_type: StatementType,
        fiscal_year: str,
        metrics: Dict[str, float],
        notes: Optional[List[str]] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        period_type: Optional[str] = None
    ) -> FinancialStatement:
        """Create a new financial statement for a company."""
        # Validate company exists
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise ValueError(f"Company with id {company_id} not found")
        
        # Check if statement already exists
        existing_statement = await self.statement_repo.get_by_company_and_type(
            company_id, statement_type, fiscal_year
        )
        if existing_statement:
            raise ValueError(f"{statement_type.value} for {fiscal_year} already exists for this company")
        
        # Create financial metrics
        financial_metrics = []
        for name, value in metrics.items():
            financial_metrics.append(FinancialMetric(
                metric_name=name,
                metric_value=value
            ))
        
        # Create financial notes
        financial_notes = []
        if notes:
            for note_text in notes:
                financial_notes.append(FinancialNote(
                    note=note_text
                ))
        
        # Create financial statement
        statement = FinancialStatement(
            statement_type=statement_type,
            fiscal_year=fiscal_year,
            period_start=period_start,
            period_end=period_end,
            period_type=period_type,
            metrics=financial_metrics,
            notes=financial_notes
        )
        
        return await self.statement_repo.create(statement, company_id)
    
    async def get_financial_statement(self, statement_id: uuid.UUID) -> Optional[FinancialStatement]:
        """Get a financial statement by its ID."""
        return await self.statement_repo.get_by_id(statement_id)
    
    async def get_financial_statement_by_type(
        self,
        company_id: uuid.UUID,
        statement_type: StatementType,
        fiscal_year: str
    ) -> Optional[FinancialStatement]:
        """Get a financial statement by company, type and fiscal year."""
        return await self.statement_repo.get_by_company_and_type(
            company_id, statement_type, fiscal_year
        )
    
    async def list_financial_statements(
        self,
        company_id: uuid.UUID,
        statement_type: Optional[StatementType] = None
    ) -> List[FinancialStatement]:
        """List financial statements for a company."""
        return await self.statement_repo.list_by_company(company_id, statement_type)
    
    async def update_financial_statement(
        self,
        statement_id: uuid.UUID,
        metrics: Optional[Dict[str, float]] = None,
        notes: Optional[List[str]] = None,
        fiscal_year: Optional[str] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        period_type: Optional[str] = None
    ) -> FinancialStatement:
        """Update a financial statement."""
        statement = await self.statement_repo.get_by_id(statement_id)
        if not statement:
            raise ValueError(f"Financial statement with id {statement_id} not found")
        
        # Update fields if provided
        if fiscal_year:
            statement.fiscal_year = fiscal_year
        if period_start:
            statement.period_start = period_start
        if period_end:
            statement.period_end = period_end
        if period_type:
            statement.period_type = period_type
        
        # Update metrics if provided
        if metrics:
            updated_metrics = []
            # Convert existing metrics to a dictionary for lookup
            existing_metrics = {metric.metric_name: metric for metric in statement.metrics}
            
            for name, value in metrics.items():
                if name in existing_metrics:
                    # Update existing metric
                    metric = existing_metrics[name]
                    metric.metric_value = value
                    updated_metrics.append(metric)
                else:
                    # Create new metric
                    updated_metrics.append(FinancialMetric(
                        metric_name=name,
                        metric_value=value
                    ))
            
            # Keep metrics that weren't updated
            for name, metric in existing_metrics.items():
                if name not in metrics:
                    updated_metrics.append(metric)
            
            statement.metrics = updated_metrics
        
        # Update notes if provided
        if notes:
            statement.notes = [FinancialNote(note=note_text) for note_text in notes]
        
        return await self.statement_repo.update(statement)
    
    async def delete_financial_statement(self, statement_id: uuid.UUID) -> bool:
        """Delete a financial statement."""
        return await self.statement_repo.delete(statement_id)
    
    async def get_financial_metric(
        self,
        company_id: uuid.UUID,
        metric_name: str,
        statement_type: StatementType,
        fiscal_year: str
    ) -> Optional[float]:
        """Get a specific financial metric value."""
        statement = await self.statement_repo.get_by_company_and_type(
            company_id, statement_type, fiscal_year
        )
        
        if not statement:
            return None
        
        for metric in statement.metrics:
            if metric.metric_name == metric_name:
                return metric.metric_value
        
        return None
    
    async def compare_financial_metrics(
        self,
        company_id: uuid.UUID,
        metric_name: str,
        statement_type: StatementType,
        fiscal_years: List[str]
    ) -> Dict[str, Optional[float]]:
        """Compare a financial metric across multiple fiscal years."""
        result = {}
        
        for fiscal_year in fiscal_years:
            value = await self.get_financial_metric(
                company_id, metric_name, statement_type, fiscal_year
            )
            result[fiscal_year] = value
        
        return result
    
    async def calculate_growth_rate(
        self,
        company_id: uuid.UUID,
        metric_name: str,
        statement_type: StatementType,
        from_year: str,
        to_year: str
    ) -> Optional[float]:
        """Calculate the growth rate of a financial metric between two fiscal years."""
        from_value = await self.get_financial_metric(
            company_id, metric_name, statement_type, from_year
        )
        
        to_value = await self.get_financial_metric(
            company_id, metric_name, statement_type, to_year
        )
        
        if from_value is None or to_value is None or from_value == 0:
            return None
        
        return ((to_value - from_value) / from_value) * 100 