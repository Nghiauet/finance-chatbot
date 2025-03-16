# Import required modules
from datetime import datetime
from typing import List, Optional, Literal, Annotated, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from bson import ObjectId
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue

# Custom ObjectId class for MongoDB document IDs
class ObjectIdPydanticAnnotation:
    @classmethod
    def validate_object_id(cls, v: Any, handler) -> ObjectId:
        if isinstance(v, ObjectId):
            return v

        s = handler(v)
        if ObjectId.is_valid(s):
            return ObjectId(s)
        else:
            raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, _handler) -> core_schema.CoreSchema:
        assert source_type is ObjectId
        return core_schema.no_info_wrap_validator_function(
            cls.validate_object_id, 
            core_schema.str_schema(), 
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema, handler) -> JsonSchemaValue:
        return handler(core_schema.str_schema())

PyObjectId = Annotated[ObjectId, ObjectIdPydanticAnnotation]

# Financial Report Schema
class FinancialReport(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    report_id: str = Field(..., description="Unique identifier for the report")
    company: str = Field(..., description="Company name")
    type: str = Field(..., description="Type of financial document")
    period: str = Field(..., description="Reporting period (e.g., Q1 2024)")
    date_created: datetime = Field(default_factory=datetime.now)
    status: str = Field(..., description="Status of the report (draft, final, etc.)")
    content: str = Field(..., description="The full text content of the financial report")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the report")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        },
        json_schema_extra={
            "example": {
                "report_id": "RPT2024-002",
                "company": "ABC Corp",
                "type": "Financial Statement",
                "period": "Q1 2024",
                "date_created": "2024-04-01T00:00:00",
                "status": "final",
                "content": "ABC Corp's financial statement for Q1 2024 shows a total revenue of $10M, with a net profit of $2M. The company's operating expenses have increased by 5% compared to last quarter.",
                "tags": ["financial", "Q1", "income statement"]
            }
        }
    )

class ChatQuery(BaseModel):
    query: str
    session_id: Optional[str] = None
    file_path: Optional[str] = None
    processed_file_path: Optional[str] = None
    company: Optional[str] = None
    years: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    metadata: Optional[Dict[str, Any]] = None

class ClearChatResponse(BaseModel):
    status: str
    message: str

