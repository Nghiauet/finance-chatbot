"""Domain model for a financial note."""

import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class FinancialNote:
    """Domain model for a financial note."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    note: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow) 