"""
API routes for company extra data endpoints.
"""

from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from domain.services import CompanyExtraService
from api.v1.schemas.company_extra_schema import CompanyExtraCreate, CompanyExtraResponse
from api.v1.deps import get_company_extra_service

router = APIRouter(prefix="/company-extras", tags=["company extras"])


@router.post("/{company_id}", response_model=CompanyExtraResponse, status_code=201)
async def add_company_extra(
    company_id: UUID,
    extra_data: CompanyExtraCreate,
    extra_service: CompanyExtraService = Depends(get_company_extra_service)
):
    """Add extra data for a company."""
    try:
        data = await extra_service.add_company_extra(
            company_id=company_id,
            category=extra_data.category,
            data=extra_data.data
        )
        return {
            "company_id": company_id,
            "category": extra_data.category,
            "data": data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{company_id}/{category}", response_model=CompanyExtraResponse)
async def get_company_extra(
    company_id: UUID,
    category: str,
    extra_service: CompanyExtraService = Depends(get_company_extra_service)
):
    """Get extra data for a company by category."""
    data = await extra_service.get_company_extra(company_id, category)
    if not data:
        raise HTTPException(status_code=404, detail=f"No data found for category: {category}")
    
    return {
        "company_id": company_id,
        "category": category,
        "data": data
    }


@router.get("/{company_id}", response_model=List[str])
async def list_company_extra_categories(
    company_id: UUID,
    extra_service: CompanyExtraService = Depends(get_company_extra_service)
):
    """List all categories of extra data for a company."""
    categories = await extra_service.list_company_extra_categories(company_id)
    return categories


@router.put("/{company_id}/{category}", response_model=CompanyExtraResponse)
async def update_company_extra(
    company_id: UUID,
    category: str,
    extra_data: Dict[str, Any],
    extra_service: CompanyExtraService = Depends(get_company_extra_service)
):
    """Update extra data for a company."""
    try:
        data = await extra_service.update_company_extra(
            company_id=company_id,
            category=category,
            data=extra_data
        )
        return {
            "company_id": company_id,
            "category": category,
            "data": data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{company_id}/{category}", status_code=204)
async def delete_company_extra(
    company_id: UUID,
    category: str,
    extra_service: CompanyExtraService = Depends(get_company_extra_service)
):
    """Delete extra data for a company by category."""
    deleted = await extra_service.delete_company_extra(company_id, category)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No data found for category: {category}") 