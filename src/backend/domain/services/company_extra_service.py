"""Service for company extra data related business logic."""

import uuid
from typing import List, Dict, Any, Optional

from domain.repositories import CompanyExtraRepository, CompanyRepository


class CompanyExtraService:
    """Service for company extra data related business logic."""
    
    def __init__(
        self, 
        extra_repo: CompanyExtraRepository,
        company_repo: CompanyRepository
    ):
        self.extra_repo = extra_repo
        self.company_repo = company_repo
    
    async def add_company_extra(
        self,
        company_id: uuid.UUID,
        category: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add extra data for a company."""
        # Validate company exists
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise ValueError(f"Company with id {company_id} not found")
        
        # Validate category
        if not category:
            raise ValueError("Category is required")
        
        # Add extra data
        return await self.extra_repo.create(company_id, category, data)
    
    async def get_company_extra(
        self,
        company_id: uuid.UUID,
        category: str
    ) -> Optional[Dict[str, Any]]:
        """Get extra data for a company by category."""
        return await self.extra_repo.get_by_category(company_id, category)
    
    async def list_company_extra_categories(
        self,
        company_id: uuid.UUID
    ) -> List[str]:
        """List all categories of extra data for a company."""
        return await self.extra_repo.list_categories(company_id)
    
    async def update_company_extra(
        self,
        company_id: uuid.UUID,
        category: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update extra data for a company."""
        # Validate company exists
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise ValueError(f"Company with id {company_id} not found")
        
        return await self.extra_repo.update(company_id, category, data)
    
    async def delete_company_extra(
        self,
        company_id: uuid.UUID,
        category: str
    ) -> bool:
        """Delete extra data for a company by category."""
        return await self.extra_repo.delete(company_id, category) 