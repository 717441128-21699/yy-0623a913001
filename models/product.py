from sqlalchemy import Column, String, Integer, Float, Text, JSON
from .base import BaseModel


class Product(BaseModel):
    __tablename__ = "products"

    name = Column(String(200), nullable=False, index=True, comment="产品标准名称")
    brand = Column(String(100), nullable=False, index=True, comment="品牌")
    specification = Column(String(200), nullable=False, comment="规格/型号")
    unit = Column(String(20), nullable=False, comment="单位")
    category = Column(String(100), nullable=False, index=True, comment="产品分类")
    stock = Column(Integer, default=0, comment="库存数量")
    price = Column(Float, default=0.0, comment="单价")
    aliases = Column(JSON, default=list, comment="别名列表")
    similar_products = Column(JSON, default=list, comment="可替代产品ID列表")
    remark = Column(Text, nullable=True, comment="备注")
