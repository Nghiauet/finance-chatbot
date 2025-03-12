"""Domain model for a financial statement."""

import uuid
from datetime import datetime, date
from typing import List, Optional
from dataclasses import dataclass, field

from .financial_metric import FinancialMetric
from .financial_note import FinancialNote
from .statement_type import StatementType


@dataclass
class FinancialStatement:
    """Domain model for a financial statement."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    statement_type: StatementType
    fiscal_year: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    period_type: Optional[str] = None
    metrics: List[FinancialMetric] = field(default_factory=list)
    notes: List[FinancialNote] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)