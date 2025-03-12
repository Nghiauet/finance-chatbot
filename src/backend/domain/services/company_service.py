"""Service for company-related business logic."""

import uuid
from typing import List, Optional

from domain.models import Company
from domain.repositories import CompanyRepository


class CompanyService:
    """Service for company-related business logic."""
    
    def __init__(self, company_repo: CompanyRepository):
        self.company_repo = company_repo
    
    async def create_company(
        self, 
        name: str, 
        ticker: Optional[str] = None, 
        industry: Optional[str] = None, 
        country: Optional[str] = None
    ) -> Company:
        """Create a new company."""
        # Validate input
        if not name:
            raise ValueError("Company name is required")
        
        # Check if company with the same ticker already exists
        if ticker:
            existing_company = await self.company_repo.get_by_ticker(ticker)
            if existing_company:
                raise ValueError(f"Company with ticker {ticker} already exists")
        
        # Create company
        company = Company(
            name=name,
            ticker=ticker,
            industry=industry,
            country=country
        )
        
        return await self.company_repo.create(company)
    
    async def get_company(self, company_id: uuid.UUID) -> Optional[Company]:
        """Get a company by its ID."""
        return await self.company_repo.get_by_id(company_id)
    
    async def get_company_by_ticker(self, ticker: str) -> Optional[Company]:
        """Get a company by its ticker."""
        return await self.company_repo.get_by_ticker(ticker)
    
    async def update_company(
        self, 
        company_id: uuid.UUID, 
        name: Optional[str] = None, 
        ticker: Optional[str] = None, 
        industry: Optional[str] = None, 
        country: Optional[str] = None
    ) -> Company:
        """Update a company."""
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise ValueError(f"Company with id {company_id} not found")
        
        # Update fields if provided
        if name:
            company.name = name
        if ticker:
            # Check if ticker is already used by another company
            existing_company = await self.company_repo.get_by_ticker(ticker)
            if existing_company and existing_company.id != company_id:
                raise ValueError(f"Company with ticker {ticker} already exists")
            company.ticker = ticker
        if industry:
            company.industry = industry
        if country:
            company.country = country
        
        return await self.company_repo.update(company)
    
    async def delete_company(self, company_id: uuid.UUID) -> bool:
        """Delete a company."""
        return await self.company_repo.delete(company_id)
    
    async def list_companies(self, limit: int = 100, offset: int = 0) -> List[Company]:
        """List companies with pagination."""
        return await self.company_repo.list_companies(limit, offset) 