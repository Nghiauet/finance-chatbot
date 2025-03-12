from uuid import UUID
from pydantic import BaseModel
from typing import Optional

class CompanyCreateRequest(BaseModel):
    name: str
    ticker: Optional[str]

class CompanyResponse(BaseModel):
    id: UUID
    name: str
    ticker: Optional[str]

    class Config:
        orm_mode = True