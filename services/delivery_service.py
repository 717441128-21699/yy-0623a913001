from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from models import Order, OrderStatus, DeliveryHandover, DeliveryUrgency
from schemas import DeliveryHandoverUpdate, DeliveryUrgency as DeliveryUrgencySchema
from services import OrderService


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.order_service = OrderService(db)

    def _get_urgency_display(self, urgency: DeliveryUrgency) -> str:
        mapping = {
            DeliveryUrgency.URGENT_SURGERY: "【紧急】下午手术前必须到",
            DeliveryUrgency.URGENT_TODAY: "【加急】今日必须送达",
            DeliveryUrgency.NORMAL: "【常规】正常配送",
            DeliveryUrgency.NEXT_BATCH: "【常规】可随下次常规配送"
        }
        return mapping.get(urgency, "【常规】正常配送")

    def _generate_items_summary(self, order: Order) -> str:
        parts = []
        for item in order.items:
            qty_str = f"{item.quantity}{item.unit}"
            if item.is_stock_out and item.stock_out_quantity > 0:
                actual_qty = item.quantity - item.stock_out_quantity
                qty_str = f"{actual_qty}{item.unit}"
                if item.alternative_product_name:
                    qty_str += f" (含替代{item.alternative_product_name}{item.stock_out_quantity}{item.unit})"
                else:
                    qty_str += f" (缺货{item.stock_out_quantity}{item.unit})"
            parts.append(f"{item.product_name} {item.product_spec} × {qty_str}")
        return "\n".join(parts)

    def create_handover(self, order_id: int) -> Optional[DeliveryHandover]:
        order = self.order_service.get_by_id(order_id)
        if not order:
            return None

        existing = self.db.query(DeliveryHandover).filter(DeliveryHandover.order_id == order_id).first()
        if existing:
            return existing

        urgency = DeliveryUrgency.NORMAL
        urgency_note = None

        if order.urgent_note:
            note_lower = order.urgent_note.lower()
            if "手术" in order.urgent_note or "surgery" in note_lower:
                urgency = DeliveryUrgency.URGENT_SURGERY
                urgency_note = "下午手术前必须到"
            elif "急" in order.urgent_note or "urgent" in note_lower or "今天" in order.urgent_note:
                urgency = DeliveryUrgency.URGENT_TODAY
                urgency_note = "今日必须送达"
            elif "下次" in order.urgent_note or "不急" in order.urgent_note:
                urgency = DeliveryUrgency.NEXT_BATCH
                urgency_note = "可随下次常规配送"

        handover = DeliveryHandover(
            order_id=order.id,
            order_no=order.order_no,
            clinic_name=order.clinic_name,
            urgency=urgency,
            urgency_note=urgency_note,
            items_summary=self._generate_items_summary(order),
            total_items=len(order.items),
            status="pending"
        )

        self.db.add(handover)
        self.db.commit()
        self.db.refresh(handover)
        return handover

    def get_by_order_id(self, order_id: int) -> Optional[DeliveryHandover]:
        return self.db.query(DeliveryHandover).filter(DeliveryHandover.order_id == order_id).first()

    def get_by_id(self, handover_id: int) -> Optional[DeliveryHandover]:
        return self.db.query(DeliveryHandover).filter(DeliveryHandover.id == handover_id).first()

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str = None,
        urgency: DeliveryUrgency = None
    ) -> Tuple[List[DeliveryHandover], int]:
        query = self.db.query(DeliveryHandover)
        if status:
            query = query.filter(DeliveryHandover.status == status)
        if urgency:
            query = query.filter(DeliveryHandover.urgency == urgency)
        total = query.count()
        handovers = query.order_by(
            DeliveryHandover.urgency,
            DeliveryHandover.created_at.desc()
        ).offset(skip).limit(limit).all()
        return handovers, total

    def list_for_warehouse(self, skip: int = 0, limit: int = 50) -> Tuple[List[DeliveryHandover], int]:
        return self.list(skip=skip, limit=limit, status="pending")

    def list_for_driver(self, skip: int = 0, limit: int = 50) -> Tuple[List[DeliveryHandover], int]:
        return self.list(skip=skip, limit=limit, status="packed")

    def update(self, handover_id: int, update_in: DeliveryHandoverUpdate) -> Optional[DeliveryHandover]:
        handover = self.get_by_id(handover_id)
        if not handover:
            return None

        update_data = update_in.model_dump(exclude_unset=True)

        if "urgency" in update_data and update_data["urgency"]:
            handover.urgency = update_data["urgency"]
            handover.urgency_note = self._get_urgency_display(update_data["urgency"])
        if "urgency_note" in update_data and update_data["urgency_note"]:
            handover.urgency_note = update_data["urgency_note"]
        if "package_note" in update_data:
            handover.package_note = update_data["package_note"]
        if "driver_note" in update_data:
            handover.driver_note = update_data["driver_note"]

        if "status" in update_data and update_data["status"]:
            old_status = handover.status
            new_status = update_data["status"]
            operator = update_data.get("operator")

            handover.status = new_status
            if new_status == "packed" and old_status != "packed":
                handover.packed_by = operator
                handover.packed_at = datetime.now()
            elif new_status == "dispatched" and old_status != "dispatched":
                handover.dispatched_by = operator
                handover.dispatched_at = datetime.now()
                order = self.order_service.get_by_id(handover.order_id)
                if order:
                    self.order_service.update_status(order.id, OrderStatus.DELIVERING, operator)
            elif new_status == "delivered" and old_status != "delivered":
                handover.delivered_by = operator
                handover.delivered_at = datetime.now()
                order = self.order_service.get_by_id(handover.order_id)
                if order:
                    self.order_service.update_status(order.id, OrderStatus.COMPLETED, operator)

        self.db.commit()
        self.db.refresh(handover)
        return handover

    def print_handover(self, handover_id: int) -> Optional[DeliveryHandover]:
        handover = self.get_by_id(handover_id)
        if not handover:
            return None
        handover.printed_at = datetime.now()
        self.db.commit()
        self.db.refresh(handover)
        return handover

    def get_urgency_statistics(self) -> dict:
        query = self.db.query(DeliveryHandover).filter(
            DeliveryHandover.status.in_(["pending", "packed"])
        )
        stats = {
            "urgent_surgery": 0,
            "urgent_today": 0,
            "normal": 0,
            "next_batch": 0
        }
        for handover in query.all():
            stats[handover.urgency.value] = stats.get(handover.urgency.value, 0) + 1
        return stats
