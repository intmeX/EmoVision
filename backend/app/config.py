"""
全局配置管理模块

使用 pydantic-settings 管理环境变量和配置
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # 服务配置
    app_name: str = Field(default="EmoVision", description="应用名称")
    app_version: str = Field(default="0.1.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    host: str = Field(default="0.0.0.0", description="服务主机")
    port: int = Field(default=8000, description="服务端口")
    
    # CORS配置
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="允许的跨域来源"
    )
    
    # 模型配置
    models_dir: Path = Field(
        default=Path("models"),
        description="模型权重目录"
    )
    yolo_model_size: Literal["n", "s", "m", "l", "x"] = Field(
        default="m",
        description="YOLO模型尺寸"
    )
    
    # 设备配置
    device: Literal["auto", "cuda", "cpu"] = Field(
        default="auto",
        description="推理设备: auto/cuda/cpu"
    )
    
    # 上传配置
    upload_dir: Path = Field(
        default=Path("uploads"),
        description="上传文件目录"
    )
    max_upload_size: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="最大上传文件大小(字节)"
    )
    
    # WebSocket配置
    ws_heartbeat_interval: int = Field(
        default=30,
        description="WebSocket心跳间隔(秒)"
    )
    
    def get_device(self) -> str:
        """获取实际使用的设备"""
        if self.device == "auto":
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        return self.device


# 全局配置实例
settings = Settings()
