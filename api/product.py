from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas import Product, ProductCreate, ProductUpdate, ProductMatchResult
from schemas.base import ApiResponse, PaginatedResponse
from services import ProductService

router = APIRouter(prefix="/products", tags=["产品目录"])


@router.post("", response_model=ApiResponse[Product])
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    service = ProductService(db)
    product = service.create(product_in)
    return ApiResponse(data=product, message="创建成功")


@router.get("", response_model=ApiResponse[PaginatedResponse[Product]])
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str = Query(None),
    keyword: str = Query(None),
    db: Session = Depends(get_db)
):
    service = ProductService(db)
    skip = (page - 1) * page_size
    products, total = service.list(skip=skip, limit=page_size, category=category, keyword=keyword)
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=products,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/{product_id}", response_model=ApiResponse[Product])
def get_product(product_id: int, db: Session = Depends(get_db)):
    service = ProductService(db)
    product = service.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return ApiResponse(data=product)


@router.put("/{product_id}", response_model=ApiResponse[Product])
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    service = ProductService(db)
    product = service.update(product_id, product_in)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return ApiResponse(data=product, message="更新成功")


@router.delete("/{product_id}", response_model=ApiResponse[bool])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    service = ProductService(db)
    success = service.delete(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="产品不存在")
    return ApiResponse(data=True, message="删除成功")


@router.post("/match", response_model=ApiResponse[ProductMatchResult])
def match_product(raw_text: str = Query(..., description="原始文本"), db: Session = Depends(get_db)):
    service = ProductService(db)
    result = service.fuzzy_match(raw_text)
    return ApiResponse(data=result)


@router.post("/batch-match", response_model=ApiResponse[List[ProductMatchResult]])
def batch_match_products(raw_texts: List[str], db: Session = Depends(get_db)):
    service = ProductService(db)
    results = service.batch_match(raw_texts)
    return ApiResponse(data=results)


@router.get("/{product_id}/alternatives", response_model=ApiResponse[List[Product]])
def get_alternatives(product_id: int, db: Session = Depends(get_db)):
    service = ProductService(db)
    alternatives = service.get_alternative_products(product_id)
    return ApiResponse(data=alternatives)


@router.post("/{product_id}/stock", response_model=ApiResponse[Product])
def update_stock(
    product_id: int,
    quantity_change: int = Query(..., description="库存变化量，正数增加，负数减少"),
    db: Session = Depends(get_db)
):
    service = ProductService(db)
    product = service.update_stock(product_id, quantity_change)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return ApiResponse(data=product, message="库存更新成功")
