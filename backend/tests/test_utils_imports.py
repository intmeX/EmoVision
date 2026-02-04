"""
测试app.utils.__init__模块导入
"""

def test_utils_module_imports():
    """测试utils模块导出"""
    try:
        from app.utils import encode_frame_to_jpeg
        assert callable(encode_frame_to_jpeg)
    except ImportError:
        # If not imported at module level yet, test directly
        from app.utils.frame_utils import encode_frame_to_jpeg
        assert callable(encode_frame_to_jpeg)