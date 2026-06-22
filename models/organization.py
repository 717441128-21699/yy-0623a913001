from sqlalchemy import Column, String, Text
from .base import BaseModel


class Clinic(BaseModel):
    __tablename__ = "clinics"

    name = Column(String(200), nullable=False, index=True, comment="诊所名称")
    contact_person = Column(String(50), nullable=False, comment="联系人")
    phone = Column(String(20), nullable=False, index=True, comment="联系电话")
    address = Column(String(500), nullable=False, comment="地址")
    remark = Column(Text, nullable=True, comment="备注")
