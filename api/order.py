from fastapi import APIRouter, Depends, Query, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from schemas import Order, OrderCreate, OrderUpdate, OrderSource, OrderStatus, OrderItemCreate, OrderImage
from schemas.base import ApiResponse, PaginatedResponse
from services import OrderService, ImageService
from exceptions import OrderNotFoundException, OrderEmptyException

router = APIRouter(prefix="/orders", tags=["订单管理"])


@router.post("", response_model=ApiResponse[Order])
def create_order(order_in: OrderCreate, created_by: str = Query("system"), db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.create(order_in, created_by=created_by)
    return ApiResponse(data=order, message="创建成功")


@router.post("/with-image", response_model=ApiResponse[Order])
async def create_order_with_image(
    clinic_id: int = Form(...),
    clinic_name: str = Form(...),
    source: OrderSource = Form(OrderSource.WECHAT),
    source_detail: Optional[str] = Form(None),
    raw_content: Optional[str] = Form(""),
    customer_remark: Optional[str] = Form(None),
    urgent_note: Optional[str] = Form(None),
    created_by: str = Form("system"),
    images: list[UploadFile] = File(default_factory=list),
    db: Session = Depends(get_db)
):
    order_service = OrderService(db)
    image_service = ImageService(db)

    if not raw_content and not images:
        raise OrderEmptyException("请至少提供文字内容或上传一张图片")

    order_in = OrderCreate(
        clinic_id=clinic_id,
        clinic_name=clinic_name,
        source=source,
        source_detail=source_detail,
        raw_content=raw_content or "",
        customer_remark=customer_remark,
        urgent_note=urgent_note
    )
    order = order_service.create(order_in, created_by=created_by)

    for img_file in images:
        img = await image_service.upload_image(order.id, img_file, upload_by=created_by)
        image_service.recognize_text_mock(img.id)

    db.refresh(order)
    return ApiResponse(data=order, message="创建成功，图片已识别")


@router.post("/{order_id}/images", response_model=ApiResponse[list[OrderImage]])
async def upload_order_images(
    order_id: int,
    images: list[UploadFile] = File(...),
    upload_by: str = Form("system"),
    db: Session = Depends(get_db)
):
    order_service = OrderService(db)
    order = order_service.get_by_id(order_id)
    if not order:
        raise OrderNotFoundException(order_id)

    image_service = ImageService(db)
    result = []
    for img_file in images:
        img = await image_service.upload_image(order_id, img_file, upload_by=upload_by)
        recognized = image_service.recognize_text_mock(img.id)
        result.append(recognized or img)

    db.refresh(order)
    return ApiResponse(data=result, message="上传成功")


@router.get("/{order_id}/images", response_model=ApiResponse[list[OrderImage]])
def get_order_images(order_id: int, db: Session = Depends(get_db)):
    order_service = OrderService(db)
    order = order_service.get_by_id(order_id)
    if not order:
        raise OrderNotFoundException(order_id)

    image_service = ImageService(db)
    images = image_service.list_by_order(order_id)
    return ApiResponse(data=images)


@router.put("/images/{image_id}/recognized-text", response_model=ApiResponse[OrderImage])
def update_recognized_text(
    image_id: int,
    recognized_text: str = Form(...),
    operator: str = Form("system"),
    db: Session = Depends(get_db)
):
    image_service = ImageService(db)
    img = image_service.update_recognized_text(image_id, recognized_text, operator=operator)
    if not img:
        raise HTTPException(status_code=404, detail="图片不存在")
    return ApiResponse(data=img, message="识别文本已更新")


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
        raise OrderNotFoundException(order_id)
    return ApiResponse(data=order)


@router.get("/no/{order_no}", response_model=ApiResponse[Order])
def get_order_by_no(order_no: str, db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.get_by_no(order_no)
    if not order:
        raise OrderNotFoundException()
    return ApiResponse(data=order)


@router.put("/{order_id}", response_model=ApiResponse[Order])
def update_order(order_id: int, order_in: OrderUpdate, db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.update(order_id, order_in)
    if not order:
        raise OrderNotFoundException(order_id)
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
        raise OrderNotFoundException(order_id)
    return ApiResponse(data=order, message="状态更新成功")


@router.post("/{order_id}/items", response_model=ApiResponse[Order])
def add_order_items(order_id: int, items: list[OrderItemCreate], db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.add_order_items(order_id, items)
    if not order:
        raise OrderNotFoundException(order_id)
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
