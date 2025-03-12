"""
Schema definitions for company extra data.
"""

from typing import List, Dict, Any
from uuid import UUID
from pydantic import BaseModel


class CompanyExtraCreate(BaseModel):
    """Schema for creating company extra data."""
    category: str
    data: Dict[str, Any]


class CompanyExtraResponse(BaseModel):
    """Schema for company extra response."""
    company_id: UUID
    category: str
    data: Dict[str, Any]

    class Config:
        orm_mode = True 