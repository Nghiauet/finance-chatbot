"""Domain model for a financial metric."""

import uuid
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class FinancialMetric:
    """Domain model for a financial metric."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    metric_name: str
    metric_value: float
    created_at: datetime = field(default_factory=datetime.utcnow)