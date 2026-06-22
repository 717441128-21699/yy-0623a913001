from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from models import Order, OrderItem, OrderStatus, OrderSource, Clinic
from schemas import OrderCreate, OrderUpdate, OrderItemCreate


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def _generate_order_no(self) -> str:
        now = datetime.now()
        prefix = now.strftime("%Y%m%d%H%M")
        suffix = str(uuid.uuid4().int)[:4]
        return f"DD{prefix}{suffix}"

    def create(self, order_in: OrderCreate, created_by: str = None) -> Order:
        order_no = self._generate_order_no()
        db_order = Order(
            **order_in.model_dump(exclude={"id", "created_at", "updated_at", "items"}),
            order_no=order_no,
            created_by=created_by
        )
        self.db.add(db_order)
        self.db.flush()
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def add_order_items(self, order_id: int, items: List[OrderItemCreate]) -> Order:
        db_order = self.get_by_id(order_id)
        if not db_order:
            return None
        for item in items:
            db_item = OrderItem(
                **item.model_dump(exclude={"id", "created_at", "updated_at"}),
                order_id=order_id
            )
            self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def get_by_id(self, order_id: int) -> Optional[Order]:
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_by_no(self, order_no: str) -> Optional[Order]:
        return self.db.query(Order).filter(Order.order_no == order_no).first()

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        status: OrderStatus = None,
        source: OrderSource = None,
        clinic_id: int = None,
        keyword: str = None
    ) -> Tuple[List[Order], int]:
        query = self.db.query(Order)
        if status:
            query = query.filter(Order.status == status)
        if source:
            query = query.filter(Order.source == source)
        if clinic_id:
            query = query.filter(Order.clinic_id == clinic_id)
        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.filter(
                (Order.order_no.like(keyword_pattern)) |
                (Order.clinic_name.like(keyword_pattern)) |
                (Order.raw_content.like(keyword_pattern))
            )
        total = query.count()
        orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
        return orders, total

    def update_status(self, order_id: int, status: OrderStatus, operator: str = None) -> Optional[Order]:
        db_order = self.get_by_id(order_id)
        if not db_order:
            return None
        db_order.status = status
        if status == OrderStatus.COLLATED:
            db_order.collated_by = operator
            db_order.collated_at = datetime.now()
        elif status == OrderStatus.STOCK_CONFIRMED:
            db_order.stock_checked_by = operator
            db_order.stock_checked_at = datetime.now()
        elif status == OrderStatus.PENDING_DELIVERY:
            db_order.delivery_arranged_by = operator
            db_order.delivery_arranged_at = datetime.now()
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def update(self, order_id: int, order_in: OrderUpdate) -> Optional[Order]:
        db_order = self.get_by_id(order_id)
        if not db_order:
            return None
        update_data = order_in.model_dump(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
        for field, value in update_data.items():
            setattr(db_order, field, value)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def delete_order_item(self, order_item_id: int) -> bool:
        db_item = self.db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
        if not db_item:
            return False
        self.db.delete(db_item)
        self.db.commit()
        return True

    def get_pending_collate(self, skip: int = 0, limit: int = 20) -> Tuple[List[Order], int]:
        return self.list(skip=skip, limit=limit, status=OrderStatus.PENDING_COLLATE)

    def get_pending_stock_check(self, skip: int = 0, limit: int = 20) -> Tuple[List[Order], int]:
        return self.list(skip=skip, limit=limit, status=OrderStatus.PENDING_STOCK_CHECK)

    def get_pending_delivery(self, skip: int = 0, limit: int = 20) -> Tuple[List[Order], int]:
        return self.list(skip=skip, limit=limit, status=OrderStatus.PENDING_DELIVERY)


class ClinicService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, clinic_in) -> Clinic:
        db_clinic = Clinic(**clinic_in.model_dump(exclude={"id", "created_at", "updated_at"}))
        self.db.add(db_clinic)
        self.db.commit()
        self.db.refresh(db_clinic)
        return db_clinic

    def get_by_id(self, clinic_id: int) -> Optional[Clinic]:
        return self.db.query(Clinic).filter(Clinic.id == clinic_id).first()

    def list(self, skip: int = 0, limit: int = 100, keyword: str = None) -> Tuple[List[Clinic], int]:
        query = self.db.query(Clinic)
        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.filter(
                (Clinic.name.like(keyword_pattern)) |
                (Clinic.contact_person.like(keyword_pattern)) |
                (Clinic.phone.like(keyword_pattern))
            )
        total = query.count()
        clinics = query.offset(skip).limit(limit).all()
        return clinics, total

    def update(self, clinic_id: int, clinic_in) -> Optional[Clinic]:
        db_clinic = self.get_by_id(clinic_id)
        if not db_clinic:
            return None
        update_data = clinic_in.model_dump(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
        for field, value in update_data.items():
            setattr(db_clinic, field, value)
        self.db.commit()
        self.db.refresh(db_clinic)
        return db_clinic
