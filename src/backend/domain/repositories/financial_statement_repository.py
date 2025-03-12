"""
Repository interface for FinancialStatement entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import uuid

from ..domain.models import FinancialStatement, StatementType


class FinancialStatementRepository(ABC):
    """Repository interface for FinancialStatement entities."""

    @abstractmethod
    async def create(self, statement: FinancialStatement, company_id: uuid.UUID) -> FinancialStatement:
        """Create a new financial statement for a company."""
        pass

    @abstractmethod
    async def get_by_id(self, statement_id: uuid.UUID) -> Optional[FinancialStatement]:
        """Get a financial statement by its ID."""
        pass

    @abstractmethod
    async def get_by_company_and_type(
            self,
            company_id: uuid.UUID,
            statement_type: StatementType,
            fiscal_year: str
    ) -> Optional[FinancialStatement]:
        """Get a financial statement by company, type and fiscal year."""
        pass

    @abstractmethod
    async def list_by_company(
            self,
            company_id: uuid.UUID,
            statement_type: Optional[StatementType] = None
    ) -> List[FinancialStatement]:
        """List financial statements for a company, optionally filtered by type."""
        pass

    @abstractmethod
    async def update(self, statement: FinancialStatement) -> FinancialStatement:
        """Update a financial statement."""
        pass

    @abstractmethod
    async def delete(self, statement_id: uuid.UUID) -> bool:
        """Delete a financial statement by its ID."""
        pass
