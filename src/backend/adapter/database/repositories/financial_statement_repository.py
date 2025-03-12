"""SQLAlchemy implementation of the FinancialStatementRepository."""

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from domain.models import FinancialStatement as DomainFinancialStatement
from domain.models import StatementType
from domain.repositories import FinancialStatementRepository

from ..models import FinancialStatement


class SQLAlchemyFinancialStatementRepository(FinancialStatementRepository):
    """SQLAlchemy implementation of the FinancialStatementRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, statement: DomainFinancialStatement, company_id: uuid.UUID) -> DomainFinancialStatement:
        """Create a new financial statement for a company."""
        db_statement = FinancialStatement(
            id=statement.id,
            company_id=company_id,
            statement_type=statement.statement_type.value,
            fiscal_year=statement.fiscal_year,
            period_start=statement.period_start,
            period_end=statement.period_end,
            period_type=statement.period_type,
            created_at=statement.created_at
        )
        self.session.add(db_statement)
        await self.session.flush()
        await self.session.commit()
        return await self.get_by_id(db_statement.id)

    async def get_by_id(self, statement_id: uuid.UUID) -> Optional[DomainFinancialStatement]:
        """Get a financial statement by its ID."""
        query = select(FinancialStatement).where(FinancialStatement.id == statement_id)
        result = await self.session.execute(query)
        db_statement = result.scalars().first()

        if not db_statement:
            return None

        return DomainFinancialStatement(
            id=db_statement.id,
            statement_type=StatementType(db_statement.statement_type),
            fiscal_year=db_statement.fiscal_year,
            period_start=db_statement.period_start,
            period_end=db_statement.period_end,
            period_type=db_statement.period_type,
            created_at=db_statement.created_at
        )

    async def get_by_company_and_type(
            self,
            company_id: uuid.UUID,
            statement_type: StatementType,
            fiscal_year: str
    ) -> Optional[DomainFinancialStatement]:
        """Get a financial statement by company, type and fiscal year."""
        query = select(FinancialStatement).where(
            FinancialStatement.company_id == company_id,
            FinancialStatement.statement_type == statement_type.value,
            FinancialStatement.fiscal_year == fiscal_year
        )
        result = await self.session.execute(query)
        db_statement = result.scalars().first()

        if not db_statement:
            return None

        return DomainFinancialStatement(
            id=db_statement.id,
            statement_type=StatementType(db_statement.statement_type),
            fiscal_year=db_statement.fiscal_year,
            period_start=db_statement.period_start,
            period_end=db_statement.period_end,
            period_type=db_statement.period_type,
            created_at=db_statement.created_at
        )

    async def list_by_company(
            self,
            company_id: uuid.UUID,
            statement_type: Optional[StatementType] = None
    ) -> List[DomainFinancialStatement]:
        """List financial statements for a company, optionally filtered by type."""
        if statement_type:
            query = select(FinancialStatement).where(
                FinancialStatement.company_id == company_id,
                FinancialStatement.statement_type == statement_type.value
            )
        else:
            query = select(FinancialStatement).where(FinancialStatement.company_id == company_id)

        result = await self.session.execute(query)
        db_statements = result.scalars().all()

        statements = []
        for db_statement in db_statements:
            statements.append(DomainFinancialStatement(
                id=db_statement.id,
                statement_type=StatementType(db_statement.statement_type),
                fiscal_year=db_statement.fiscal_year,
                period_start=db_statement.period_start,
                period_end=db_statement.period_end,
                period_type=db_statement.period_type,
                created_at=db_statement.created_at
            ))

        return statements

    async def update(self, statement: DomainFinancialStatement) -> DomainFinancialStatement:
        """Update a financial statement."""
        query = select(FinancialStatement).where(FinancialStatement.id == statement.id)
        result = await self.session.execute(query)
        db_statement = result.scalars().first()

        if not db_statement:
            raise ValueError(f"Financial statement with id {statement.id} not found")

        db_statement.statement_type = statement.statement_type.value
        db_statement.fiscal_year = statement.fiscal_year
        db_statement.period_start = statement.period_start
        db_statement.period_end = statement.period_end
        db_statement.period_type = statement.period_type

        await self.session.commit()
        return await self.get_by_id(statement.id)

    async def delete(self, statement_id: uuid.UUID) -> bool:
        """Delete a financial statement by its ID."""
        query = delete(FinancialStatement).where(FinancialStatement.id == statement_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0 