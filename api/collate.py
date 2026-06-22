from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import OrderCollateRequest, OrderCollateResponse
from schemas.base import ApiResponse
from services import CollateService

router = APIRouter(prefix="/workspace/collate", tags=["工作区-订单整理"])


@router.get("/preview/{order_id}", response_model=ApiResponse[OrderCollateResponse])
def preview_collate(order_id: int, db: Session = Depends(get_db)):
    service = CollateService(db)
    result = service.pre_collate(order_id)
    return ApiResponse(data=result)


@router.post("/confirm", response_model=ApiResponse[OrderCollateResponse])
def confirm_collate(request: OrderCollateRequest, db: Session = Depends(get_db)):
    service = CollateService(db)
    result = service.confirm_collate(request)
    if not result.success:
        return ApiResponse(code=400, message="部分项目未确认", data=result, success=False)
    return ApiResponse(data=result, message="整理完成")
