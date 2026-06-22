from .base import BaseSchema, PaginatedResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class OrderImageBase(BaseSchema):
    order_id: int
    file_name: str
    file_path: str
    file_size: int = 0
    mime_type: Optional[str] = None
    upload_by: Optional[str] = None
    recognized_text: Optional[str] = None
    recognized_at: Optional[datetime] = None
    status: str = "pending"
    recognize_remark: Optional[str] = None


class OrderImageCreate(OrderImageBase):
    pass


class OrderImage(OrderImageBase):
    id: int


class OperationLogBase(BaseSchema):
    order_id: int
    handover_id: Optional[int] = None
    operation_type: str
    operation_content: Optional[str] = None
    operator: str
    remark: Optional[str] = None


class OperationLogCreate(OperationLogBase):
    pass


class OperationLog(OperationLogBase):
    id: int
