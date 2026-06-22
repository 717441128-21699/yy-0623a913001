from .product import router as product_router
from .order import router as order_router
from .collate import router as collate_router
from .stock import router as stock_router
from .delivery import router as delivery_router
from .clinic import router as clinic_router

__all__ = [
    "product_router",
    "order_router",
    "collate_router",
    "stock_router",
    "delivery_router",
    "clinic_router"
]
