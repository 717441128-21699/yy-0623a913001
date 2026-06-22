from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, Enum
from .base import BaseModel
import enum


class DeliveryUrgency(str, enum.Enum):
    URGENT_SURGERY = "urgent_surgery"
    URGENT_TODAY = "urgent_today"
    NORMAL = "normal"
    NEXT_BATCH = "next_batch"


class DeliveryHandover(BaseModel):
    __tablename__ = "delivery_handovers"

    order_id = Column(Integer, nullable=False, unique=True, index=True, comment="订单ID")
    order_no = Column(String(32), nullable=False, index=True, comment="订单编号")
    clinic_name = Column(String(200), nullable=False, comment="诊所名称")
    urgency = Column(Enum(DeliveryUrgency), default=DeliveryUrgency.NORMAL, comment="紧急程度")
    urgency_note = Column(String(500), nullable=True, comment="加急说明")
    package_note = Column(Text, nullable=True, comment="打包备注")
    driver_note = Column(Text, nullable=True, comment="司机备注")
    items_summary = Column(Text, nullable=False, comment="物品清单摘要")
    total_items = Column(Integer, default=0, comment="物品总件数")
    status = Column(String(20), default="pending", comment="状态")

    printed_at = Column(DateTime, nullable=True, comment="打印时间")
    packed_by = Column(String(50), nullable=True, comment="打包人")
    packed_at = Column(DateTime, nullable=True, comment="打包时间")
    dispatched_by = Column(String(50), nullable=True, comment="发货人")
    dispatched_at = Column(DateTime, nullable=True, comment="发货时间")
    delivered_by = Column(String(50), nullable=True, comment="签收人")
    delivered_at = Column(DateTime, nullable=True, comment="签收时间")
