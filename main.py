from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from database import engine, Base
from api import (
    product_router,
    order_router,
    clinic_router,
    collate_router,
    stock_router,
    delivery_router
)
from exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="面向牙科供应商客服团队的后端订单协同服务，提供订单整理、缺货回复、配送交接三个工作区",
    version="1.1.0",
    lifespan=lifespan
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["根路径"])
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.1.0",
        "docs": "/docs",
        "api_prefix": settings.API_V1_STR
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "healthy"}


api_prefix = settings.API_V1_STR
app.include_router(product_router, prefix=api_prefix)
app.include_router(order_router, prefix=api_prefix)
app.include_router(clinic_router, prefix=api_prefix)
app.include_router(collate_router, prefix=api_prefix)
app.include_router(stock_router, prefix=api_prefix)
app.include_router(delivery_router, prefix=api_prefix)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
