import enum
from .base import BaseSchema
from .auxiliary import OperationLog
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class CollateItem(BaseModel):
    raw_text: str = Field(..., description="原始文本片段")
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    specification: Optional[str] = None
    brand: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[float] = None
    has_same_name_diff_spec: bool = False
    same_name_products: List[dict] = Field(default_factory=list)
    match_confidence: float = 0.0
    manual_confirmed: bool = False
    remark: Optional[str] = None


class OrderCollateRequest(BaseModel):
    order_id: int
    items: List[CollateItem]
    operator: str


class OrderCollateResponse(BaseModel):
    order_id: int
    items: List[CollateItem]
    warnings: List[str] = Field(default_factory=list)
    success: bool


class DeliveryUrgency(str, enum.Enum):
    URGENT_SURGERY = "urgent_surgery"
    URGENT_TODAY = "urgent_today"
    NORMAL = "normal"
    NEXT_BATCH = "next_batch"


class StockOutItem(BaseModel):
    order_item_id: int
    product_id: int
    product_name: str
    specification: str
    required_quantity: float
    stock_available: float
    stock_out_quantity: float
    alternative_product_id: Optional[int] = None
    alternative_product_name: Optional[str] = None
    alternative_spec: Optional[str] = None
    expected_restock_date: Optional[date] = None
    split_delivery: bool = False
    process_remark: Optional[str] = None


class StockOutResponse(BaseModel):
    order_id: int
    has_stock_out: bool
    stock_out_items: List[StockOutItem]
    all_in_stock_items: List[dict] = Field(default_factory=list)


class StockOutProcessRequest(BaseModel):
    order_id: int
    items: List[StockOutItem]
    operator: str


class ReplyGenerateRequest(BaseModel):
    order_id: int
    stock_out_items: Optional[List[StockOutItem]] = None
    reply_template: Optional[str] = None


class ReplyGenerateResponse(BaseModel):
    order_id: int
    reply_content: str
    summary: str


class DeliveryStockOutInfo(BaseModel):
    product_name: str
    specification: str
    stock_out_quantity: float
    alternative_product_name: Optional[str] = None
    alternative_spec: Optional[str] = None
    expected_restock_date: Optional[date] = None
    split_delivery: bool = False
    process_remark: Optional[str] = None


class DeliveryHandoverBase(BaseSchema):
    order_id: int
    order_no: str
    clinic_name: str
    urgency: DeliveryUrgency = DeliveryUrgency.NORMAL
    urgency_note: Optional[str] = None
    package_note: Optional[str] = None
    driver_note: Optional[str] = None
    items_summary: str
    total_items: int


class DeliveryHandover(DeliveryHandoverBase):
    id: int
    status: str = "pending"
    stock_out_info: List[DeliveryStockOutInfo] = Field(default_factory=list)
    operation_logs: List[OperationLog] = Field(default_factory=list)
    printed_at: Optional[datetime] = None
    packed_by: Optional[str] = None
    packed_at: Optional[datetime] = None
    dispatched_by: Optional[str] = None
    dispatched_at: Optional[datetime] = None
    delivered_by: Optional[str] = None
    delivered_at: Optional[datetime] = None


class DeliveryHandoverUpdate(BaseModel):
    urgency: Optional[DeliveryUrgency] = None
    urgency_note: Optional[str] = None
    package_note: Optional[str] = None
    driver_note: Optional[str] = None
    status: Optional[str] = None
    operator: Optional[str] = None
    remark: Optional[str] = None
