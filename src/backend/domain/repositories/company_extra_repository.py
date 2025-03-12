"""
Repository interface for CompanyExtra entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import uuid


class CompanyExtraRepository(ABC):
    """Repository interface for CompanyExtra entities."""

    @abstractmethod
    async def create(self, company_id: uuid.UUID, category: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new extra data for a company."""
        pass

    @abstractmethod
    async def get_by_category(self, company_id: uuid.UUID, category: str) -> Optional[Dict[str, Any]]:
        """Get company extra data by category."""
        pass

    @abstractmethod
    async def list_categories(self, company_id: uuid.UUID) -> List[str]:
        """List all categories of extra data for a company."""
        pass

    @abstractmethod
    async def update(self, company_id: uuid.UUID, category: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update extra data for a company."""
        pass

    @abstractmethod
    async def delete(self, company_id: uuid.UUID, category: str) -> bool:
        """Delete extra data for a company by category."""
        pass 