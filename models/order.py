from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, Enum, JSON, Date
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


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


class Order(BaseModel):
    __tablename__ = "orders"

    order_no = Column(String(32), nullable=False, unique=True, index=True, comment="订单编号")
    clinic_id = Column(Integer, nullable=False, index=True, comment="诊所ID")
    clinic_name = Column(String(200), nullable=False, comment="诊所名称")
    source = Column(Enum(OrderSource), nullable=False, index=True, comment="订单来源")
    source_detail = Column(String(200), nullable=True, comment="来源详情")
    raw_content = Column(Text, nullable=False, comment="原始需求内容")
    ocr_content = Column(Text, nullable=True, comment="图片OCR识别文本(可编辑)")
    customer_remark = Column(Text, nullable=True, comment="客户备注")
    urgent_note = Column(String(500), nullable=True, comment="加急说明")
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING_COLLATE, index=True, comment="订单状态")

    created_by = Column(String(50), nullable=True, comment="创建人")
    collated_by = Column(String(50), nullable=True, comment="整理人")
    collated_at = Column(DateTime, nullable=True, comment="整理时间")
    stock_checked_by = Column(String(50), nullable=True, comment="库存确认人")
    stock_checked_at = Column(DateTime, nullable=True, comment="库存确认时间")
    delivery_arranged_by = Column(String(50), nullable=True, comment="配送安排人")
    delivery_arranged_at = Column(DateTime, nullable=True, comment="配送安排时间")

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    images = relationship("OrderImage", cascade="all, delete-orphan")
    operation_logs = relationship("OperationLog", cascade="all, delete-orphan")


class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, nullable=False, index=True, comment="产品ID")
    product_name = Column(String(200), nullable=False, comment="产品名称")
    product_spec = Column(String(200), nullable=False, comment="产品规格")
    brand = Column(String(100), nullable=False, comment="品牌")
    unit = Column(String(20), nullable=False, comment="单位")
    quantity = Column(Float, nullable=False, comment="数量")
    price = Column(Float, default=0.0, comment="单价")
    remark = Column(Text, nullable=True, comment="备注")

    is_stock_out = Column(Integer, default=0, comment="是否缺货 0否 1是")
    stock_available = Column(Float, default=0, comment="检查时可用库存")
    stock_out_quantity = Column(Float, default=0, comment="缺货数量")
    alternative_product_id = Column(Integer, nullable=True, comment="替代产品ID")
    alternative_product_name = Column(String(200), nullable=True, comment="替代产品名称")
    alternative_product_spec = Column(String(200), nullable=True, comment="替代产品规格")
    expected_restock_date = Column(Date, nullable=True, comment="预计补货日期")
    split_delivery = Column(Integer, default=0, comment="是否拆单 0否 1是")
    stock_process_remark = Column(Text, nullable=True, comment="缺货处理说明")
    stock_processed_by = Column(String(50), nullable=True, comment="缺货处理人")
    stock_processed_at = Column(DateTime, nullable=True, comment="缺货处理时间")

    order = relationship("Order", back_populates="items")
