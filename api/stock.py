from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    StockOutResponse, StockOutProcessRequest,
    ReplyGenerateRequest, ReplyGenerateResponse
)
from schemas.base import ApiResponse
from services import StockService

router = APIRouter(prefix="/workspace/stock", tags=["工作区-缺货回复"])


@router.get("/check/{order_id}", response_model=ApiResponse[StockOutResponse])
def check_stock(order_id: int, db: Session = Depends(get_db)):
    service = StockService(db)
    result = service.check_stock(order_id)
    return ApiResponse(data=result)


@router.post("/process", response_model=ApiResponse[StockOutResponse])
def process_stock_out(request: StockOutProcessRequest, db: Session = Depends(get_db)):
    service = StockService(db)
    result = service.process_stock_out(request)
    return ApiResponse(data=result, message="库存处理完成")


@router.post("/generate-reply", response_model=ApiResponse[ReplyGenerateResponse])
def generate_reply(request: ReplyGenerateRequest, db: Session = Depends(get_db)):
    service = StockService(db)
    result = service.generate_reply(request)
    return ApiResponse(data=result)
