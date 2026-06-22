from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from models import Order, OrderStatus, DeliveryHandover, DeliveryUrgency, OrderItem
from schemas import (
    DeliveryHandoverUpdate, DeliveryUrgency as DeliveryUrgencySchema,
    DeliveryStockOutInfo, DeliveryHandover as DeliveryHandoverSchema
)
from services.order_service import OrderService
from services.auxiliary_service import OperationLogService
from exceptions import OrderNotFoundException, OrderEmptyException, ResourceNotFoundException


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.order_service = OrderService(db)
        self.log_service = OperationLogService(db)

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

    def _get_stock_out_info(self, order: Order) -> List[DeliveryStockOutInfo]:
        result = []
        for item in order.items:
            if item.is_stock_out or item.stock_out_quantity > 0:
                result.append(DeliveryStockOutInfo(
                    product_name=item.product_name,
                    specification=item.product_spec,
                    stock_out_quantity=item.stock_out_quantity,
                    alternative_product_name=item.alternative_product_name,
                    alternative_spec=item.alternative_product_spec,
                    expected_restock_date=item.expected_restock_date,
                    split_delivery=bool(item.split_delivery),
                    process_remark=item.stock_process_remark
                ))
        return result

    def _enrich_handover(self, handover: DeliveryHandover) -> dict:
        order = self.order_service.get_by_id(handover.order_id)
        data = {
            "id": handover.id,
            "order_id": handover.order_id,
            "order_no": handover.order_no,
            "clinic_name": handover.clinic_name,
            "urgency": handover.urgency,
            "urgency_note": handover.urgency_note,
            "package_note": handover.package_note,
            "driver_note": handover.driver_note,
            "items_summary": handover.items_summary,
            "total_items": handover.total_items,
            "status": handover.status,
            "stock_out_info": [],
            "operation_logs": [],
            "printed_at": handover.printed_at,
            "packed_by": handover.packed_by,
            "packed_at": handover.packed_at,
            "dispatched_by": handover.dispatched_by,
            "dispatched_at": handover.dispatched_at,
            "delivered_by": handover.delivered_by,
            "delivered_at": handover.delivered_at,
            "created_at": handover.created_at,
            "updated_at": handover.updated_at
        }
        if order:
            data["stock_out_info"] = [x.model_dump() for x in self._get_stock_out_info(order)]
            if order.urgent_note and not data["urgency_note"]:
                data["urgency_note"] = order.urgent_note
        logs = self.log_service.list_by_handover(handover.id)
        data["operation_logs"] = [
            {
                "id": log.id,
                "order_id": log.order_id,
                "handover_id": log.handover_id,
                "operation_type": log.operation_type,
                "operation_content": log.operation_content,
                "operator": log.operator,
                "remark": log.remark,
                "created_at": log.created_at
            }
            for log in logs
        ]
        return data

    def create_handover(self, order_id: int, operator: str = "system"):
        order = self.order_service.get_by_id(order_id)
        if not order:
            raise OrderNotFoundException(order_id)

        if not order.items:
            raise OrderEmptyException(f"订单 {order_id} 尚未整理订单项，请先完成整理")

        existing = self.db.query(DeliveryHandover).filter(DeliveryHandover.order_id == order_id).first()
        if existing:
            self.log_service.create_log(
                order_id=order_id,
                handover_id=existing.id,
                operation_type="delivery_view",
                operation_content="查看已有配送交接单",
                operator=operator
            )
            return self._enrich_handover(existing)

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
        self.db.flush()

        self.log_service.create_log(
            order_id=order_id,
            handover_id=handover.id,
            operation_type="delivery_create",
            operation_content=f"创建配送交接单，紧急程度：{urgency.value}",
            operator=operator
        )

        self.db.commit()
        self.db.refresh(handover)
        return self._enrich_handover(handover)

    def get_by_order_id(self, order_id: int):
        handover = self.db.query(DeliveryHandover).filter(DeliveryHandover.order_id == order_id).first()
        if not handover:
            return None
        return self._enrich_handover(handover)

    def get_by_id(self, handover_id: int):
        handover = self.db.query(DeliveryHandover).filter(DeliveryHandover.id == handover_id).first()
        if not handover:
            raise ResourceNotFoundException(f"配送交接单 {handover_id} 不存在")
        return self._enrich_handover(handover)

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str = None,
        urgency: DeliveryUrgency = None
    ) -> Tuple[List[dict], int]:
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
        enriched = [self._enrich_handover(h) for h in handovers]
        return enriched, total

    def list_for_warehouse(self, skip: int = 0, limit: int = 50) -> Tuple[List[dict], int]:
        return self.list(skip=skip, limit=limit, status="pending")

    def list_for_driver(self, skip: int = 0, limit: int = 50) -> Tuple[List[dict], int]:
        return self.list(skip=skip, limit=limit, status="packed")

    def update(self, handover_id: int, update_in: DeliveryHandoverUpdate):
        handover = self.db.query(DeliveryHandover).filter(DeliveryHandover.id == handover_id).first()
        if not handover:
            raise ResourceNotFoundException(f"配送交接单 {handover_id} 不存在")

        update_data = update_in.model_dump(exclude_unset=True)
        operator = update_data.get("operator", "system")
        remark = update_data.get("remark")
        content_parts = []

        if "urgency" in update_data and update_data["urgency"]:
            handover.urgency = update_data["urgency"]
            handover.urgency_note = self._get_urgency_display(update_data["urgency"])
            content_parts.append(f"调整紧急程度为 {update_data['urgency'].value}")
        if "urgency_note" in update_data and update_data["urgency_note"]:
            handover.urgency_note = update_data["urgency_note"]
            content_parts.append(f"更新加急备注")
        if "package_note" in update_data:
            handover.package_note = update_data["package_note"]
            content_parts.append(f"更新打包备注")
        if "driver_note" in update_data:
            handover.driver_note = update_data["driver_note"]
            content_parts.append(f"更新司机备注")

        if "status" in update_data and update_data["status"]:
            old_status = handover.status
            new_status = update_data["status"]

            status_map = {
                "packed": "打包完成",
                "dispatched": "已发货",
                "delivered": "已签收"
            }

            if new_status == "packed" and old_status != "packed":
                handover.packed_by = operator
                handover.packed_at = datetime.now()
                content_parts.append(f"状态变更为：{status_map.get(new_status, new_status)}")
            elif new_status == "dispatched" and old_status != "dispatched":
                handover.dispatched_by = operator
                handover.dispatched_at = datetime.now()
                order = self.order_service.get_by_id(handover.order_id)
                if order:
                    self.order_service.update_status(order.id, OrderStatus.DELIVERING, operator)
                content_parts.append(f"状态变更为：{status_map.get(new_status, new_status)}")
            elif new_status == "delivered" and old_status != "delivered":
                handover.delivered_by = operator
                handover.delivered_at = datetime.now()
                order = self.order_service.get_by_id(handover.order_id)
                if order:
                    self.order_service.update_status(order.id, OrderStatus.COMPLETED, operator)
                content_parts.append(f"状态变更为：{status_map.get(new_status, new_status)}")

            handover.status = new_status

        if content_parts:
            self.log_service.create_log(
                order_id=handover.order_id,
                handover_id=handover.id,
                operation_type="delivery_update",
                operation_content="；".join(content_parts),
                operator=operator,
                remark=remark
            )

        self.db.commit()
        self.db.refresh(handover)
        return self._enrich_handover(handover)

    def print_handover(self, handover_id: int, operator: str = "system"):
        handover = self.db.query(DeliveryHandover).filter(DeliveryHandover.id == handover_id).first()
        if not handover:
            raise ResourceNotFoundException(f"配送交接单 {handover_id} 不存在")
        handover.printed_at = datetime.now()

        self.log_service.create_log(
            order_id=handover.order_id,
            handover_id=handover.id,
            operation_type="delivery_print",
            operation_content="打印交接单",
            operator=operator
        )

        self.db.commit()
        self.db.refresh(handover)
        return self._enrich_handover(handover)

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
