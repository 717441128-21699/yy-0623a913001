import os
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile

from models import OrderImage, OrderImageStatus, OperationLog, Order
from schemas import OrderImageCreate, OperationLogCreate


class OperationLogService:
    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        order_id: int,
        operation_type: str,
        operation_content: str = None,
        operator: str = "system",
        remark: str = None,
        handover_id: int = None
    ) -> OperationLog:
        log_in = OperationLogCreate(
            order_id=order_id,
            handover_id=handover_id,
            operation_type=operation_type,
            operation_content=operation_content,
            operator=operator,
            remark=remark
        )
        log = OperationLog(**log_in.model_dump())
        self.db.add(log)
        self.db.flush()
        return log

    def list_by_order(self, order_id: int, limit: int = 50) -> List[OperationLog]:
        return (
            self.db.query(OperationLog)
            .filter(OperationLog.order_id == order_id)
            .order_by(OperationLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_by_handover(self, handover_id: int) -> List[OperationLog]:
        return (
            self.db.query(OperationLog)
            .filter(OperationLog.handover_id == handover_id)
            .order_by(OperationLog.created_at.desc())
            .all()
        )


class ImageService:
    UPLOAD_DIR = "uploads/orders"

    def __init__(self, db: Session):
        self.db = db
        self.log_service = OperationLogService(db)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    def _refresh_order_ocr_content(self, order_id: int):
        images = (
            self.db.query(OrderImage)
            .filter(OrderImage.order_id == order_id)
            .order_by(OrderImage.created_at.asc())
            .all()
        )
        confirmed_texts = [img.recognized_text for img in images if img.status == OrderImageStatus.CONFIRMED and img.recognized_text]
        recognized_texts = [img.recognized_text for img in images if img.status == OrderImageStatus.RECOGNIZED and img.recognized_text]
        all_texts = confirmed_texts + recognized_texts
        merged = "、".join(all_texts) if all_texts else None

        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.ocr_content = merged
            if merged and not order.raw_content:
                order.raw_content = merged
            self.db.flush()

    async def upload_image(
        self,
        order_id: int,
        file: UploadFile,
        upload_by: str = None
    ) -> OrderImage:
        file_ext = os.path.splitext(file.filename or "image.jpg")[1] or ".jpg"
        unique_name = f"{order_id}_{uuid.uuid4().hex}{file_ext}"
        save_path = os.path.join(self.UPLOAD_DIR, unique_name)

        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        img_in = OrderImageCreate(
            order_id=order_id,
            file_name=file.filename or unique_name,
            file_path=save_path,
            file_size=len(content),
            mime_type=file.content_type,
            upload_by=upload_by,
            status="pending"
        )
        img = OrderImage(**img_in.model_dump())
        self.db.add(img)
        self.db.flush()

        self.log_service.create_log(
            order_id=order_id,
            operation_type="image_upload",
            operation_content=f"上传图片: {file.filename}",
            operator=upload_by or "system"
        )
        self.db.commit()
        self.db.refresh(img)
        return img

    def recognize_text_mock(self, image_id: int, recognized_text: str = None) -> Optional[OrderImage]:
        img = self.db.query(OrderImage).filter(OrderImage.id == image_id).first()
        if not img:
            return None

        if recognized_text is None:
            recognized_text = "3M树脂A2两支、麻醉针30G一盒、洁牙头五支"

        img.recognized_text = recognized_text
        img.recognized_at = datetime.now()
        img.status = OrderImageStatus.RECOGNIZED

        self.log_service.create_log(
            order_id=img.order_id,
            operation_type="image_ocr",
            operation_content=f"图片识别完成: {img.file_name}",
            operator="ocr_system"
        )
        self._refresh_order_ocr_content(img.order_id)
        self.db.commit()
        self.db.refresh(img)
        return img

    def update_recognized_text(
        self,
        image_id: int,
        recognized_text: str,
        operator: str = None
    ) -> Optional[OrderImage]:
        img = self.db.query(OrderImage).filter(OrderImage.id == image_id).first()
        if not img:
            return None

        img.recognized_text = recognized_text
        img.status = OrderImageStatus.CONFIRMED

        self.log_service.create_log(
            order_id=img.order_id,
            operation_type="image_ocr_edit",
            operation_content=f"编辑图片识别文本: {img.file_name}",
            operator=operator or "system"
        )
        self._refresh_order_ocr_content(img.order_id)
        self.db.commit()
        self.db.refresh(img)
        return img

    def list_by_order(self, order_id: int) -> List[OrderImage]:
        return (
            self.db.query(OrderImage)
            .filter(OrderImage.order_id == order_id)
            .order_by(OrderImage.created_at.desc())
            .all()
        )
