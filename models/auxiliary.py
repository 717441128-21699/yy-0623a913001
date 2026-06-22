from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class OrderImageStatus(str, enum.Enum):
    PENDING = "pending"
    RECOGNIZED = "recognized"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class OrderImage(BaseModel):
    __tablename__ = "order_images"

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True, comment="订单ID")
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_path = Column(String(500), nullable=False, comment="存储路径")
    file_size = Column(Integer, default=0, comment="文件大小(bytes)")
    mime_type = Column(String(100), nullable=True, comment="MIME类型")
    upload_by = Column(String(50), nullable=True, comment="上传人")
    recognized_text = Column(Text, nullable=True, comment="OCR识别文本")
    recognized_at = Column(DateTime, nullable=True, comment="识别时间")
    status = Column(Enum(OrderImageStatus), default=OrderImageStatus.PENDING, comment="识别状态")
    recognize_remark = Column(String(500), nullable=True, comment="识别备注")


class OperationLog(BaseModel):
    __tablename__ = "operation_logs"

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True, comment="订单ID")
    handover_id = Column(Integer, ForeignKey("delivery_handovers.id"), nullable=True, index=True, comment="交接单ID")
    operation_type = Column(String(50), nullable=False, index=True, comment="操作类型")
    operation_content = Column(Text, nullable=True, comment="操作内容")
    operator = Column(String(50), nullable=False, comment="操作人")
    remark = Column(String(500), nullable=True, comment="备注")
