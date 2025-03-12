"""
Schema definitions for chat requests and responses.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel


class ChatQueryRequest(BaseModel):
    """Schema for chat query request."""
    query: str
    company_id: Optional[UUID] = None
    context: Optional[Dict[str, Any]] = None


class ChatQueryResponse(BaseModel):
    """Schema for chat query response."""
    answer: str
    data: Optional[Dict[str, Any]] = None
    sources: Optional[List[Dict[str, Any]]] = None 