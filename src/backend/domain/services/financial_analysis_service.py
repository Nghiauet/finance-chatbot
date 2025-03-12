# domain/services/financial_analysis_service.py
from uuid import UUID
from domain.repositories.financial_statement_repository import FinancialStatementRepository

class FinancialAnalysisService:
    def __init__(self, financial_statement_repo):
        self.financial_statement_repo = financial_statement_repo

    def calculate_pe_ratio(self, company_id: UUID, fiscal_year: str):
        statement = self.financial_statement_repo.get_by_type_and_year(
            company_id, 'income_statement', fiscal_year
        )
        net_income = next((m.metric_value for m in statement.metrics if m.metric_name == 'Net Income'), None)
        market_cap = next((m.metric_value for m in statement.metrics if m.metric_name == 'Market Cap'), None)

        if net_income and market_cap:
            return market_cap / net_income
        raise ValueError("Insufficient data")