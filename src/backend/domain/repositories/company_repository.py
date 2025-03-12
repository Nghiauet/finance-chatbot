"""
Repository interface for Company entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import uuid

from ..domain.models import Company


class CompanyRepository(ABC):
    """Repository interface for Company entities."""

    @abstractmethod
    async def create(self, company: Company) -> Company:
        """Create a new company."""
        pass

    @abstractmethod
    async def get_by_id(self, company_id: uuid.UUID) -> Optional[Company]:
        """Get a company by its ID."""
        pass

    @abstractmethod
    async def get_by_ticker(self, ticker: str) -> Optional[Company]:
        """Get a company by its ticker symbol."""
        pass

    @abstractmethod
    async def list_companies(self, limit: int = 100, offset: int = 0) -> List[Company]:
        """List companies with pagination."""
        pass

    @abstractmethod
    async def update(self, company: Company) -> Company:
        """Update a company."""
        pass

    @abstractmethod
    async def delete(self, company_id: uuid.UUID) -> bool:
        """Delete a company by its ID."""
        pass
