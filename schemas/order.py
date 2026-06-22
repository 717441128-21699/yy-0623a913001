import enum
from .base import BaseSchema, PaginatedResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class OrderSource(str, enum.Enum):
    WECHAT = "wechat"
    PHONE = "phone"
    MINIAPP = "miniapp"
    OTHER = "other"


class OrderStatus(str, enum.Enum):
    PENDING_COLLATE = "pending_c"
    COLLATED = "collated"
    PENDING_STOCK_CHECK = "pending_stock"
    STOCK_CONFIRMED = "stock_confirmed"
    PENDING_DELIVERY = "pending_delivery"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderItemBase(BaseSchema):
    product_id: int
    product_name: str
    product_spec: str
    brand: str
    unit: str
    quantity: float
    price: float
    remark: Optional[str] = None


class OrderItemCreate(OrderItemBase):
    pass


class OrderItem(OrderItemBase):
    id: int
    order_id: int
    is_stock_out: bool = False
    stock_out_quantity: float = 0
    alternative_product_id: Optional[int] = None
    alternative_product_name: Optional[str] = None


class OrderBase(BaseSchema):
    clinic_id: int
    clinic_name: str
    source: OrderSource
    source_detail: Optional[str] = Field(default=None, description="来源详情，如微信号、手机号")
    raw_content: str = Field(..., description="原始需求内容")
    customer_remark: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING_COLLATE
    urgent_note: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(OrderBase):
    clinic_id: Optional[int] = None
    clinic_name: Optional[str] = None
    source: Optional[OrderSource] = None
    raw_content: Optional[str] = None
    status: Optional[OrderStatus] = None


class Order(OrderBase):
    id: int
    order_no: str
    items: List[OrderItem] = Field(default_factory=list)
    created_by: Optional[str] = None
    collated_by: Optional[str] = None
    collated_at: Optional[datetime] = None
    stock_checked_by: Optional[str] = None
    stock_checked_at: Optional[datetime] = None
    delivery_arranged_by: Optional[str] = None
    delivery_arranged_at: Optional[datetime] = None


class OrderListResponse(PaginatedResponse[Order]):
    pass
