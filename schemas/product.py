from .base import BaseSchema
from pydantic import BaseModel, Field
from typing import Optional, List


class ProductBase(BaseSchema):
    name: str = Field(..., description="产品标准名称")
    brand: str = Field(..., description="品牌")
    specification: str = Field(..., description="规格/型号")
    unit: str = Field(..., description="单位")
    category: str = Field(..., description="产品分类")
    stock: int = Field(default=0, description="库存数量")
    price: float = Field(default=0.0, description="单价")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    similar_products: List[int] = Field(default_factory=list, description="可替代产品ID列表")
    remark: Optional[str] = Field(default=None, description="备注")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    name: Optional[str] = None
    brand: Optional[str] = None
    specification: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None


class Product(ProductBase):
    id: int


class ProductMatchResult(BaseModel):
    matched: bool
    confidence: float
    product: Optional[Product] = None
    similar_products: List[Product] = Field(default_factory=list, description="同名不同型号的产品")
    raw_text: str
    parsed_quantity: Optional[float] = None
    parsed_unit: Optional[str] = None
    suggestion: Optional[str] = None
