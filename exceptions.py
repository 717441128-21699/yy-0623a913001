from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from typing import Any
import logging

logger = logging.getLogger(__name__)


class BusinessException(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class ResourceNotFoundException(BusinessException):
    def __init__(self, message: str = "资源不存在", data: Any = None):
        super().__init__(404, message, data)


class OrderNotFoundException(ResourceNotFoundException):
    def __init__(self, order_id: int = None):
        msg = f"订单不存在" if order_id is None else f"订单 {order_id} 不存在"
        super().__init__(msg, {"order_id": order_id})


class OrderEmptyException(BusinessException):
    def __init__(self, message: str = "订单内容为空，无法处理"):
        super().__init__(400, message)


class InvalidStateException(BusinessException):
    def __init__(self, message: str = "当前状态不允许此操作"):
        super().__init__(400, message)


def register_exception_handlers(app):
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        logger.warning(f"业务异常: code={exc.code}, message={exc.message}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": exc.data,
                "success": False
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            loc = " -> ".join(str(x) for x in err.get("loc", []))
            errors.append(f"{loc}: {err.get('msg', '校验失败')}")
        message = "参数校验失败: " + "; ".join(errors)
        logger.warning(f"参数校验失败: {message}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 422,
                "message": message,
                "data": None,
                "success": False
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"数据库异常: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 500,
                "message": "数据库操作失败",
                "data": None,
                "success": False
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"未捕获异常: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 500,
                "message": "服务内部错误",
                "data": None,
                "success": False
            }
        )
