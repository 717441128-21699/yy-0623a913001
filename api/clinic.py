from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import Clinic, ClinicCreate
from schemas.base import ApiResponse, PaginatedResponse
from services.order_service import ClinicService

router = APIRouter(prefix="/clinics", tags=["诊所管理"])


@router.post("", response_model=ApiResponse[Clinic])
def create_clinic(clinic_in: ClinicCreate, db: Session = Depends(get_db)):
    service = ClinicService(db)
    clinic = service.create(clinic_in)
    return ApiResponse(data=clinic, message="创建成功")


@router.get("", response_model=ApiResponse[PaginatedResponse[Clinic]])
def list_clinics(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(None),
    db: Session = Depends(get_db)
):
    service = ClinicService(db)
    skip = (page - 1) * page_size
    clinics, total = service.list(skip=skip, limit=page_size, keyword=keyword)
    total_pages = (total + page_size - 1) // page_size
    return ApiResponse(
        data=PaginatedResponse(
            items=clinics,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/{clinic_id}", response_model=ApiResponse[Clinic])
def get_clinic(clinic_id: int, db: Session = Depends(get_db)):
    service = ClinicService(db)
    clinic = service.get_by_id(clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="诊所不存在")
    return ApiResponse(data=clinic)


@router.put("/{clinic_id}", response_model=ApiResponse[Clinic])
def update_clinic(clinic_id: int, clinic_in: ClinicCreate, db: Session = Depends(get_db)):
    service = ClinicService(db)
    clinic = service.update(clinic_id, clinic_in)
    if not clinic:
        raise HTTPException(status_code=404, detail="诊所不存在")
    return ApiResponse(data=clinic, message="更新成功")
