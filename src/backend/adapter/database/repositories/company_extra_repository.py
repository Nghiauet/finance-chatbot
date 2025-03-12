"""SQLAlchemy implementation of the CompanyExtraRepository."""

import uuid
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from domain.repositories import CompanyExtraRepository

from ..models import CompanyExtra


class SQLAlchemyCompanyExtraRepository(CompanyExtraRepository):
    """SQLAlchemy implementation of the CompanyExtraRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, company_id: uuid.UUID, category: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new extra data for a company."""
        db_extra = CompanyExtra(
            company_id=company_id,
            category=category,
            data=data
        )
        self.session.add(db_extra)
        await self.session.commit()

        return data

    async def get_by_category(self, company_id: uuid.UUID, category: str) -> Optional[Dict[str, Any]]:
        """Get company extra data by category."""
        query = select(CompanyExtra).where(
            CompanyExtra.company_id == company_id,
            CompanyExtra.category == category
        )
        result = await self.session.execute(query)
        db_extra = result.scalars().first()

        if not db_extra:
            return None

        return db_extra.data

    async def list_categories(self, company_id: uuid.UUID) -> List[str]:
        """List all categories of extra data for a company."""
        query = select(CompanyExtra.category).where(CompanyExtra.company_id == company_id)
        result = await self.session.execute(query)
        categories = result.scalars().all()

        return categories

    async def update(self, company_id: uuid.UUID, category: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update extra data for a company."""
        query = select(CompanyExtra).where(
            CompanyExtra.company_id == company_id,
            CompanyExtra.category == category
        )
        result = await self.session.execute(query)
        db_extra = result.scalars().first()

        if not db_extra:
            return await self.create(company_id, category, data)

        db_extra.data = data
        await self.session.commit()

        return data

    async def delete(self, company_id: uuid.UUID, category: str) -> bool:
        """Delete extra data for a company by category."""
        query = delete(CompanyExtra).where(
            CompanyExtra.company_id == company_id,
            CompanyExtra.category == category
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0 