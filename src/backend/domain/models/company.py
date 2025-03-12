# domain/models/company.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
import uuid
from datetime import datetime, date
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .financial_statement import FinancialStatement
from .company_extra import CompanyExtra

class Company(BaseModel):
    """Domain model for a company."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str
    ticker: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    financial_statements: List[FinancialStatement] = field(default_factory=list)
    company_extras: List[CompanyExtra] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True