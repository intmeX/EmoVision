"""API路由模块"""

from fastapi import APIRouter

from .routes import pipeline, source, config, websocket

# 创建主路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["流水线控制"])
api_router.include_router(source.router, prefix="/source", tags=["视觉源管理"])
api_router.include_router(config.router, prefix="/config", tags=["配置管理"])
