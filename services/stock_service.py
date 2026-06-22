from typing import List
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session

from models import Order, OrderStatus, OrderItem, Product
from schemas import (
    StockOutResponse, StockOutItem, StockOutProcessRequest,
    ReplyGenerateRequest, ReplyGenerateResponse
)
from services.product_service import ProductService
from services.order_service import OrderService
from services.auxiliary_service import OperationLogService
from exceptions import OrderNotFoundException, OrderEmptyException


class StockService:
    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)
        self.order_service = OrderService(db)
        self.log_service = OperationLogService(db)

    def _build_stock_out_item_from_order_item(self, item: OrderItem, product: Product) -> StockOutItem:
        stock_available = product.stock
        stock_out_qty = max(0, item.quantity - stock_available)

        soi = StockOutItem(
            order_item_id=item.id,
            product_id=item.product_id,
            product_name=item.product_name,
            specification=item.product_spec,
            required_quantity=item.quantity,
            stock_available=stock_available,
            stock_out_quantity=stock_out_qty
        )

        if item.is_stock_out or item.alternative_product_id:
            soi.alternative_product_id = item.alternative_product_id
            soi.alternative_product_name = item.alternative_product_name
            soi.alternative_spec = item.alternative_product_spec
            soi.expected_restock_date = item.expected_restock_date
            soi.split_delivery = bool(item.split_delivery)
            soi.process_remark = item.stock_process_remark
            if stock_available == 0:
                soi.stock_available = item.stock_available

        return soi

    def check_stock(self, order_id: int) -> StockOutResponse:
        order = self.order_service.get_by_id(order_id)
        if not order:
            raise OrderNotFoundException(order_id)

        if not order.items:
            raise OrderEmptyException(f"订单 {order_id} 尚未整理订单项，请先完成整理")

        stock_out_items = []
        all_in_stock_items = []

        for item in order.items:
            product = self.product_service.get_by_id(item.product_id)
            if not product:
                continue

            soi = self._build_stock_out_item_from_order_item(item, product)

            if soi.stock_out_quantity > 0 and not soi.alternative_product_id:
                alternatives = self.product_service.get_alternative_products(item.product_id)
                if alternatives:
                    alt = alternatives[0]
                    soi.alternative_product_id = alt.id
                    soi.alternative_product_name = alt.name
                    soi.alternative_spec = alt.specification

            if soi.stock_out_quantity > 0 or item.is_stock_out:
                stock_out_items.append(soi)
            else:
                all_in_stock_items.append({
                    "order_item_id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "specification": item.product_spec,
                    "quantity": item.quantity,
                    "stock_available": soi.stock_available
                })

        return StockOutResponse(
            order_id=order_id,
            has_stock_out=len(stock_out_items) > 0,
            stock_out_items=stock_out_items,
            all_in_stock_items=all_in_stock_items
        )

    def process_stock_out(self, request: StockOutProcessRequest) -> StockOutResponse:
        order = self.order_service.get_by_id(request.order_id)
        if not order:
            raise OrderNotFoundException(request.order_id)

        if not request.items:
            raise OrderEmptyException("缺货处理项不能为空")

        for stock_item in request.items:
            order_item = self.db.query(OrderItem).filter(OrderItem.id == stock_item.order_item_id).first()
            if not order_item:
                continue

            order_item.is_stock_out = 1 if stock_item.stock_out_quantity > 0 else 0
            order_item.stock_available = stock_item.stock_available
            order_item.stock_out_quantity = stock_item.stock_out_quantity
            order_item.alternative_product_id = stock_item.alternative_product_id
            order_item.alternative_product_name = stock_item.alternative_product_name
            order_item.alternative_product_spec = stock_item.alternative_spec
            order_item.expected_restock_date = stock_item.expected_restock_date
            order_item.split_delivery = 1 if stock_item.split_delivery else 0
            order_item.stock_process_remark = stock_item.process_remark
            order_item.stock_processed_by = request.operator
            order_item.stock_processed_at = datetime.now()

            if stock_item.process_remark:
                if order_item.remark:
                    order_item.remark += f"; {stock_item.process_remark}"
                else:
                    order_item.remark = stock_item.process_remark

            if stock_item.alternative_product_id:
                alt_product = self.product_service.get_by_id(stock_item.alternative_product_id)
                if alt_product and alt_product.stock >= stock_item.stock_out_quantity:
                    self.product_service.update_stock(
                        stock_item.alternative_product_id,
                        -int(stock_item.stock_out_quantity)
                    )

            if stock_item.stock_out_quantity > 0 and stock_item.stock_available > 0:
                self.product_service.update_stock(
                    stock_item.product_id,
                    -int(stock_item.stock_available)
                )
            elif stock_item.stock_out_quantity == 0:
                self.product_service.update_stock(
                    stock_item.product_id,
                    -int(stock_item.required_quantity)
                )

        self.order_service.update_status(
            request.order_id,
            OrderStatus.PENDING_DELIVERY,
            operator=request.operator
        )

        self.log_service.create_log(
            order_id=request.order_id,
            operation_type="stock_process",
            operation_content=f"缺货处理完成，共{len(request.items)}项",
            operator=request.operator
        )

        self.db.commit()
        return self.check_stock(request.order_id)

    def _get_urgency_text(self, order: Order) -> str:
        if order.urgent_note:
            return f"\n【重要提醒】{order.urgent_note}"
        return ""

    def _load_saved_stock_items(self, order: Order) -> List[StockOutItem]:
        result = []
        for item in order.items:
            if not item.is_stock_out and not item.alternative_product_id:
                continue
            product = self.product_service.get_by_id(item.product_id)
            if not product:
                continue
            soi = self._build_stock_out_item_from_order_item(item, product)
            result.append(soi)
        return result

    def generate_reply(self, request: ReplyGenerateRequest) -> ReplyGenerateResponse:
        order = self.order_service.get_by_id(request.order_id)
        if not order:
            raise OrderNotFoundException(request.order_id)

        stock_out_items = request.stock_out_items
        if stock_out_items is None:
            stock_out_items = self._load_saved_stock_items(order)

        clinic_name = order.clinic_name
        parts = []
        summary_parts = []

        greeting = f"您好{clinic_name}！感谢您的订货。"
        parts.append(greeting)

        if not stock_out_items:
            success_msg = "您订购的商品全部有货，我们将尽快为您安排配送。"
            parts.append(success_msg)
            summary_parts.append("全部有货")
        else:
            stock_out_details = []
            alternative_details = []
            restock_details = []
            split_details = []

            for item in stock_out_items:
                base_info = f"{item.product_name} ({item.specification})"

                if item.alternative_product_name:
                    alt_info = f"为您更换为：{item.alternative_product_name} ({item.alternative_spec or ''})"
                    alternative_details.append(f"{base_info} 缺货 {item.stock_out_quantity}，{alt_info}")
                    summary_parts.append(f"{base_info}换替代品牌")
                elif item.expected_restock_date:
                    restock_info = f"预计补货日期：{item.expected_restock_date}"
                    restock_details.append(f"{base_info} 缺货 {item.stock_out_quantity}，{restock_info}")
                    summary_parts.append(f"{base_info}等补货")
                elif item.split_delivery:
                    split_info = f"先发现货 {item.stock_available}，补货后补发 {item.stock_out_quantity}"
                    split_details.append(f"{base_info} 缺货 {item.stock_out_quantity}，{split_info}")
                    summary_parts.append(f"{base_info}拆单发")
                else:
                    stock_out_details.append(f"{base_info} 缺货 {item.stock_out_quantity}")
                    summary_parts.append(f"{base_info}缺货")

            if alternative_details:
                parts.append("\n【替代品牌安排】")
                parts.extend(alternative_details)

            if restock_details:
                parts.append("\n【待补货安排】")
                parts.extend(restock_details)
                next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
                parts.append(f"我们会在货到后第一时间为您补发。")

            if split_details:
                parts.append("\n【拆单发货安排】")
                parts.extend(split_details)

            if stock_out_details:
                parts.append("\n【待确认缺货】")
                parts.extend(stock_out_details)
                parts.append("请您确认是否可以接受以上方案，或联系我们协商其他解决方案。")

        urgency_text = self._get_urgency_text(order)
        if urgency_text:
            parts.append(urgency_text)

        parts.append("\n如有任何问题，请随时联系我们。谢谢！")

        reply_content = "\n".join(parts)
        summary = "；".join(summary_parts) if summary_parts else "全部有货"

        self.log_service.create_log(
            order_id=request.order_id,
            operation_type="reply_generate",
            operation_content=f"生成客户回复: {summary}",
            operator="system"
        )

        return ReplyGenerateResponse(
            order_id=request.order_id,
            reply_content=reply_content,
            summary=summary
        )
