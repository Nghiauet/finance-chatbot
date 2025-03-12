"""SQLAlchemy implementation of the CompanyRepository."""

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from domain.models import Company as DomainCompany
from domain.repositories import CompanyRepository

from ..models import Company


class SQLAlchemyCompanyRepository(CompanyRepository):
    """SQLAlchemy implementation of the CompanyRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, company: DomainCompany) -> DomainCompany:
        """Create a new company."""
        db_company = Company(
            id=company.id,
            name=company.name,
            ticker=company.ticker,
            industry=company.industry,
            country=company.country,
            created_at=company.created_at
        )
        self.session.add(db_company)
        await self.session.flush()
        await self.session.commit()
        return await self.get_by_id(db_company.id)

    async def get_by_id(self, company_id: uuid.UUID) -> Optional[DomainCompany]:
        """Get a company by its ID."""
        query = select(Company).where(Company.id == company_id)
        result = await self.session.execute(query)
        db_company = result.scalars().first()

        if not db_company:
            return None

        return DomainCompany(
            id=db_company.id,
            name=db_company.name,
            ticker=db_company.ticker,
            industry=db_company.industry,
            country=db_company.country,
            created_at=db_company.created_at
        )

    async def get_by_ticker(self, ticker: str) -> Optional[DomainCompany]:
        """Get a company by its ticker symbol."""
        query = select(Company).where(Company.ticker == ticker)
        result = await self.session.execute(query)
        db_company = result.scalars().first()

        if not db_company:
            return None

        return DomainCompany(
            id=db_company.id,
            name=db_company.name,
            ticker=db_company.ticker,
            industry=db_company.industry,
            country=db_company.country,
            created_at=db_company.created_at
        )

    async def list_companies(self, limit: int = 100, offset: int = 0) -> List[DomainCompany]:
        """List companies with pagination."""
        query = select(Company).limit(limit).offset(offset)
        result = await self.session.execute(query)
        db_companies = result.scalars().all()

        companies = []
        for db_company in db_companies:
            companies.append(DomainCompany(
                id=db_company.id,
                name=db_company.name,
                ticker=db_company.ticker,
                industry=db_company.industry,
                country=db_company.country,
                created_at=db_company.created_at
            ))

        return companies

    async def update(self, company: DomainCompany) -> DomainCompany:
        """Update a company."""
        query = select(Company).where(Company.id == company.id)
        result = await self.session.execute(query)
        db_company = result.scalars().first()

        if not db_company:
            raise ValueError(f"Company with id {company.id} not found")

        db_company.name = company.name
        db_company.ticker = company.ticker
        db_company.industry = company.industry
        db_company.country = company.country

        await self.session.commit()
        return await self.get_by_id(company.id)

    async def delete(self, company_id: uuid.UUID) -> bool:
        """Delete a company by its ID."""
        query = delete(Company).where(Company.id == company_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0 