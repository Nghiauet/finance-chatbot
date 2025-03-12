"""
API routes for company endpoints.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query

from domain.services import CompanyService
from api.v1.schemas.company_schema import CompanyCreate, CompanyResponse, CompanyDetailResponse
from api.v1.deps import get_company_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    company_data: CompanyCreate,
    company_service: CompanyService = Depends(get_company_service)
):
    """Create a new company."""
    try:
        company = await company_service.create_company(
            name=company_data.name,
            ticker=company_data.ticker,
            industry=company_data.industry,
            country=company_data.country
        )
        return company
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    company_service: CompanyService = Depends(get_company_service)
):
    """List companies with pagination."""
    companies = await company_service.list_companies(limit=limit, offset=offset)
    return companies


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: UUID,
    include_statements: bool = Query(False),
    include_extras: bool = Query(False),
    company_service: CompanyService = Depends(get_company_service)
):
    """Get a company by its ID with optional details."""
    company = await company_service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Filter out statements and extras if not requested
    if not include_statements:
        company.financial_statements = []
    
    if not include_extras:
        company.company_extras = []
    
    return company


@router.get("/ticker/{ticker}", response_model=CompanyDetailResponse)
async def get_company_by_ticker(
    ticker: str,
    include_statements: bool = Query(False),
    include_extras: bool = Query(False),
    company_service: CompanyService = Depends(get_company_service)
):
    """Get a company by its ticker with optional details."""
    company = await company_service.get_company_by_ticker(ticker)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Filter out statements and extras if not requested
    if not include_statements:
        company.financial_statements = []
    
    if not include_extras:
        company.company_extras = []
    
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company_data: CompanyCreate,
    company_service: CompanyService = Depends(get_company_service)
):
    """Update a company."""
    try:
        company = await company_service.update_company(
            company_id=company_id,
            name=company_data.name,
            ticker=company_data.ticker,
            industry=company_data.industry,
            country=company_data.country
        )
        return company
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: UUID,
    company_service: CompanyService = Depends(get_company_service)
):
    """Delete a company."""
    deleted = await company_service.delete_company(company_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Company not found") 