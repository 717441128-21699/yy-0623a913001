from typing import List, Tuple
from sqlalchemy.orm import Session
import re
import jieba

from models import Order, OrderStatus
from schemas import (
    OrderCollateRequest, OrderCollateResponse, CollateItem,
    OrderItemCreate
)
from services import ProductService, OrderService


class CollateService:
    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)
        self.order_service = OrderService(db)

    def _split_raw_content(self, raw_content: str) -> List[str]:
        raw_content = raw_content.replace(" ", "")
        separators = [r'[、,，;；\n\r]+', r'[和与及]+']
        temp = raw_content
        for sep in separators:
            temp = re.sub(sep, '|', temp)
        items = [item.strip() for item in temp.split('|') if item.strip()]
        return items

    def _enrich_collate_item(self, raw_text: str) -> CollateItem:
        match_result = self.product_service.fuzzy_match(raw_text)
        item = CollateItem(
            raw_text=raw_text,
            match_confidence=match_result.confidence
        )
        if match_result.matched and match_result.product:
            item.product_id = match_result.product.id
            item.product_name = match_result.product.name
            item.specification = match_result.product.specification
            item.brand = match_result.product.brand
            item.unit = match_result.product.unit

            if match_result.parsed_quantity:
                item.quantity = match_result.parsed_quantity
            if match_result.parsed_unit:
                item.unit = match_result.parsed_unit

            item.has_same_name_diff_spec = len(match_result.similar_products) > 0
            item.same_name_products = [
                {
                    "id": p.id,
                    "name": p.name,
                    "brand": p.brand,
                    "specification": p.specification,
                    "unit": p.unit
                }
                for p in match_result.similar_products
            ]

            if match_result.suggestion:
                item.remark = match_result.suggestion

            if match_result.confidence >= 0.9:
                item.manual_confirmed = True

        return item

    def pre_collate(self, order_id: int) -> OrderCollateResponse:
        order = self.order_service.get_by_id(order_id)
        if not order:
            return OrderCollateResponse(
                order_id=order_id,
                items=[],
                warnings=["订单不存在"],
                success=False
            )

        raw_items = self._split_raw_content(order.raw_content)
        if not raw_items:
            return OrderCollateResponse(
                order_id=order_id,
                items=[],
                warnings=["未能从原始内容中解析出明细项"],
                success=False
            )

        collate_items = []
        warnings = []

        for raw_text in raw_items:
            item = self._enrich_collate_item(raw_text)
            collate_items.append(item)

            if not item.product_id:
                warnings.append(f"未匹配到产品：{raw_text}")
            elif item.has_same_name_diff_spec:
                warnings.append(f"存在同名不同规格：{raw_text}")
            elif not item.manual_confirmed:
                warnings.append(f"需人工确认：{raw_text} (匹配度{item.match_confidence:.0%})")

        return OrderCollateResponse(
            order_id=order_id,
            items=collate_items,
            warnings=warnings,
            success=True
        )

    def confirm_collate(self, request: OrderCollateRequest) -> OrderCollateResponse:
        order = self.order_service.get_by_id(request.order_id)
        if not order:
            return OrderCollateResponse(
                order_id=request.order_id,
                items=[],
                warnings=["订单不存在"],
                success=False
            )

        unconfirmed = []
        order_items = []

        for item in request.items:
            if not item.manual_confirmed and not (item.match_confidence >= 0.9):
                unconfirmed.append(item.raw_text)
                continue

            if not item.product_id or not item.quantity:
                unconfirmed.append(item.raw_text)
                continue

            product = self.product_service.get_by_id(item.product_id)
            if not product:
                unconfirmed.append(item.raw_text)
                continue

            order_item = OrderItemCreate(
                product_id=item.product_id,
                product_name=item.product_name or product.name,
                product_spec=item.specification or product.specification,
                brand=item.brand or product.brand,
                unit=item.unit or product.unit,
                quantity=item.quantity,
                price=product.price,
                remark=item.remark
            )
            order_items.append(order_item)

        if unconfirmed:
            return OrderCollateResponse(
                order_id=request.order_id,
                items=request.items,
                warnings=[f"以下项目未确认：{', '.join(unconfirmed)}"],
                success=False
            )

        self.order_service.add_order_items(request.order_id, order_items)
        self.order_service.update_status(
            request.order_id,
            OrderStatus.PENDING_STOCK_CHECK,
            operator=request.operator
        )

        return OrderCollateResponse(
            order_id=request.order_id,
            items=request.items,
            warnings=[],
            success=True
        )
