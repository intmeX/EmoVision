"""
基础单元测试
测试核心流水线功能
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np
from pathlib import Path

from app.core.pipeline import Pipeline
from app.schemas.pipeline import PipelineConfig
from app.modules.detector.schemas import Detection, DetectionType, BoundingBox
from app.modules.recognizer.schemas import EmotionResult


class TestPipeline:
    """Pipeline类基础测试"""
    
    def test_pipeline_initialization(self):
        """测试流水线初始化"""
        config = PipelineConfig()
        pipeline = Pipeline(config)
        
        assert pipeline.state.value == "idle"
        assert pipeline.config == config
        # 测试初始化后各个组件未被创建
        assert pipeline._detector is None
        assert pipeline._recognizer is None
        assert pipeline._renderer is None
    
    def test_pipeline_properties(self):
        """测试流水线属性访问"""
        config = PipelineConfig()
        pipeline = Pipeline(config)
        
        assert pipeline.state.value == "idle"
        assert pipeline.config == config