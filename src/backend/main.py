# backend/main.py (example FastAPI setup clearly)

from fastapi import FastAPI, Depends
from adapter.database.repositories.sqlalchemy_company_repository import SQLAlchemyCompanyRepository
from adapter.database.session import get_db_session
from domain.services.financial_analysis_service import FinancialAnalysisService

app = FastAPI()

@app.get("/companies/{company_id}/pe_ratio")
def pe_ratio(company_id: UUID, fiscal_year: str, db: Session = Depends(get_db_session)):
    financial_statement_repo = SQLAlchemyFinancialStatementRepository(db)
    financial_analysis_service = FinancialAnalysisService(financial_statement_repo)
    return financial_analysis_service.calculate_pe_ratio(company_id, fiscal_year)