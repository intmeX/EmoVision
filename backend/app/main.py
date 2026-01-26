"""
EmoVision 后端应用入口

FastAPI 应用主模块
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .api.routes.websocket import router as ws_router
from .api.deps import cleanup_resources
from .config import settings
from .utils.logger import setup_logger, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    setup_logger(log_level="DEBUG" if settings.debug else "INFO")
    logger = get_logger("main")
    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    
    # 确保必要目录存在
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.models_dir).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # 关闭时
    await cleanup_resources()
    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="视觉情绪识别一体化Web应用",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": settings.app_version}


# 开发模式入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
