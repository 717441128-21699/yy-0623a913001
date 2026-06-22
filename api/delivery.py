from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from schemas import DeliveryHandover, DeliveryHandoverUpdate, DeliveryUrgency
from schemas.base import ApiResponse, PaginatedResponse
from services import DeliveryService

router = APIRouter(prefix="/workspace/delivery", tags=["工作区-配送交接"])


@router.post("/create/{order_id}", response_model=ApiResponse[DeliveryHandover])
def create_handover(order_id: int, db: Session = Depends(get_db)):
    service = DeliveryService(db)
    handover = service.create_handover(order_id)
    if not handover:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(data=handover, message="交接单创建成功")


@router.get("/{handover_id}", response_model=ApiResponse[DeliveryHandover])
def get_handover(handover_id: int, db: Session = Depends(get_db)):
    service = DeliveryService(db)
    handover = service.get_by_id(handover_id)
    if not handover:
        raise HTTPException(status_code=404, detail="交接单不存在")
    return ApiResponse(data=handover)


@router.get("/order/{order_id}", response_model=ApiResponse[DeliveryHandover])
def get_handover_by_order(order_id: int, db: Session = Depends(get_db)):
    service = DeliveryService(db)
    handover = service.get_by_order_id(order_id)
    if not handover:
        raise HTTPException(status_code=404, detail="交接单不存在")
    return ApiResponse(data=handover)


@router.get("", response_model=ApiResponse[PaginatedResponse[DeliveryHandover]])
def list_handovers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    urgency: Optional[DeliveryUrgency] = Query(None),
    db: Session = Depends(get_db)
):
    service = DeliveryService(db)
    skip = (page - 1) * page_size
    handovers, total = service.list(
        skip=skip, limit=page_size,
        status=status, urgency=urgency
    )
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=handovers,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/warehouse/list", response_model=ApiResponse[PaginatedResponse[DeliveryHandover]])
def list_for_warehouse(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = DeliveryService(db)
    skip = (page - 1) * page_size
    handovers, total = service.list_for_warehouse(skip=skip, limit=page_size)
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=handovers,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/driver/list", response_model=ApiResponse[PaginatedResponse[DeliveryHandover]])
def list_for_driver(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = DeliveryService(db)
    skip = (page - 1) * page_size
    handovers, total = service.list_for_driver(skip=skip, limit=page_size)
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=handovers,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.put("/{handover_id}", response_model=ApiResponse[DeliveryHandover])
def update_handover(handover_id: int, update_in: DeliveryHandoverUpdate, db: Session = Depends(get_db)):
    service = DeliveryService(db)
    handover = service.update(handover_id, update_in)
    if not handover:
        raise HTTPException(status_code=404, detail="交接单不存在")
    return ApiResponse(data=handover, message="更新成功")


@router.post("/{handover_id}/print", response_model=ApiResponse[DeliveryHandover])
def print_handover(handover_id: int, db: Session = Depends(get_db)):
    service = DeliveryService(db)
    handover = service.print_handover(handover_id)
    if not handover:
        raise HTTPException(status_code=404, detail="交接单不存在")
    return ApiResponse(data=handover, message="已标记打印")


@router.get("/statistics/urgency", response_model=ApiResponse[dict])
def get_urgency_statistics(db: Session = Depends(get_db)):
    service = DeliveryService(db)
    stats = service.get_urgency_statistics()
    return ApiResponse(data=stats)
