"""
日志配置模块

使用 loguru 进行日志管理
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    rotation: str = "10 MB",
    retention: str = "7 days"
) -> None:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径，为 None 时仅输出到控制台
        rotation: 日志轮转大小
        retention: 日志保留时间
    """
    # 移除默认处理器
    logger.remove()
    
    # 控制台输出格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        enqueue=True
    )
    
    # 添加文件处理器
    if log_file:
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        logger.add(
            log_file,
            format=file_format,
            level=log_level,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            enqueue=True
        )


def get_logger(name: str = "emovision"):
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        配置好的日志记录器
    """
    return logger.bind(name=name)
