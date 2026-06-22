from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from schemas import Order, OrderCreate, OrderUpdate, OrderSource, OrderStatus, OrderItemCreate
from schemas.base import ApiResponse, PaginatedResponse
from services import OrderService

router = APIRouter(prefix="/orders", tags=["订单管理"])


@router.post("", response_model=ApiResponse[Order])
def create_order(order_in: OrderCreate, created_by: str = Query("system"), db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.create(order_in, created_by=created_by)
    return ApiResponse(data=order, message="创建成功")


@router.get("", response_model=ApiResponse[PaginatedResponse[Order]])
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = Query(None),
    source: Optional[OrderSource] = Query(None),
    clinic_id: Optional[int] = Query(None),
    keyword: str = Query(None),
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    skip = (page - 1) * page_size
    orders, total = service.list(
        skip=skip, limit=page_size,
        status=status, source=source,
        clinic_id=clinic_id, keyword=keyword
    )
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=orders,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/{order_id}", response_model=ApiResponse[Order])
def get_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(data=order)


@router.get("/no/{order_no}", response_model=ApiResponse[Order])
def get_order_by_no(order_no: str, db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.get_by_no(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(data=order)


@router.put("/{order_id}", response_model=ApiResponse[Order])
def update_order(order_id: int, order_in: OrderUpdate, db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.update(order_id, order_in)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(data=order, message="更新成功")


@router.patch("/{order_id}/status", response_model=ApiResponse[Order])
def update_order_status(
    order_id: int,
    status: OrderStatus,
    operator: str = Query("system"),
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    order = service.update_status(order_id, status, operator=operator)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(data=order, message="状态更新成功")


@router.post("/{order_id}/items", response_model=ApiResponse[Order])
def add_order_items(order_id: int, items: list[OrderItemCreate], db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.add_order_items(order_id, items)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(data=order, message="添加成功")


@router.delete("/items/{item_id}", response_model=ApiResponse[bool])
def delete_order_item(item_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    success = service.delete_order_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="订单项不存在")
    return ApiResponse(data=True, message="删除成功")


@router.get("/workspace/collate", response_model=ApiResponse[PaginatedResponse[Order]])
def get_pending_collate(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    skip = (page - 1) * page_size
    orders, total = service.get_pending_collate(skip=skip, limit=page_size)
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=orders,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/workspace/stock", response_model=ApiResponse[PaginatedResponse[Order]])
def get_pending_stock_check(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    skip = (page - 1) * page_size
    orders, total = service.get_pending_stock_check(skip=skip, limit=page_size)
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=orders,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/workspace/delivery", response_model=ApiResponse[PaginatedResponse[Order]])
def get_pending_delivery(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    skip = (page - 1) * page_size
    orders, total = service.get_pending_delivery(skip=skip, limit=page_size)
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=orders,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )
