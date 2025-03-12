"""Domain model for flexible company extra data."""

import uuid
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class CompanyExtra:
    """Domain model for flexible company extra data."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    category: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow) 