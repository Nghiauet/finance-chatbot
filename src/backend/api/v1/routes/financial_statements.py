"""
API routes for financial statement endpoints.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query

from domain.services import FinancialStatementService
from domain.models import StatementType
from api.v1.schemas.financial_statement_schema import (
    FinancialStatementCreate, 
    FinancialStatementResponse,
    FinancialStatementUpdate,
    StatementTypeEnum
)
from api.v1.deps import get_financial_statement_service

router = APIRouter(prefix="/financial-statements", tags=["financial statements"])


@router.post("/{company_id}", response_model=FinancialStatementResponse, status_code=201)
async def create_financial_statement(
    company_id: UUID,
    statement_data: FinancialStatementCreate,
    statement_service: FinancialStatementService = Depends(get_financial_statement_service)
):
    """Create a new financial statement for a company."""
    try:
        statement = await statement_service.create_financial_statement(
            company_id=company_id,
            statement_type=StatementType(statement_data.statement_type.value),
            fiscal_year=statement_data.fiscal_year,
            metrics=statement_data.metrics,
            notes=statement_data.notes,
            period_start=statement_data.period_start,
            period_end=statement_data.period_end,
            period_type=statement_data.period_type
        )
        return statement
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{company_id}", response_model=List[FinancialStatementResponse])
async def list_financial_statements(
    company_id: UUID,
    statement_type: Optional[StatementTypeEnum] = None,
    statement_service: FinancialStatementService = Depends(get_financial_statement_service)
):
    """List financial statements for a company."""
    statement_type_enum = StatementType(statement_type.value) if statement_type else None
    statements = await statement_service.list_financial_statements(
        company_id=company_id,
        statement_type=statement_type_enum
    )
    return statements


@router.get("/{company_id}/{statement_id}", response_model=FinancialStatementResponse)
async def get_financial_statement(
    company_id: UUID,
    statement_id: UUID,
    statement_service: FinancialStatementService = Depends(get_financial_statement_service)
):
    """Get a financial statement by its ID."""
    statement = await statement_service.get_financial_statement(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Financial statement not found")
    return statement


@router.get("/{company_id}/type/{statement_type}/year/{fiscal_year}", response_model=FinancialStatementResponse)
async def get_financial_statement_by_type_and_year(
    company_id: UUID,
    statement_type: StatementTypeEnum,
    fiscal_year: str,
    statement_service: FinancialStatementService = Depends(get_financial_statement_service)
):
    """Get a financial statement by company, type and fiscal year."""
    statement = await statement_service.get_financial_statement_by_type(
        company_id=company_id,
        statement_type=StatementType(statement_type.value),
        fiscal_year=fiscal_year
    )
    if not statement:
        raise HTTPException(status_code=404, detail="Financial statement not found")
    return statement


@router.put("/{statement_id}", response_model=FinancialStatementResponse)
async def update_financial_statement(
    statement_id: UUID,
    statement_data: FinancialStatementUpdate,
    statement_service: FinancialStatementService = Depends(get_financial_statement_service)
):
    """Update a financial statement."""
    try:
        statement = await statement_service.update_financial_statement(
            statement_id=statement_id,
            metrics=statement_data.metrics,
            notes=statement_data.notes,
            fiscal_year=statement_data.fiscal_year,
            period_start=statement_data.period_start,
            period_end=statement_data.period_end,
            period_type=statement_data.period_type
        )
        return statement
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{statement_id}", status_code=204)
async def delete_financial_statement(
    statement_id: UUID,
    statement_service: FinancialStatementService = Depends(get_financial_statement_service)
):
    """Delete a financial statement."""
    deleted = await statement_service.delete_financial_statement(statement_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Financial statement not found") 