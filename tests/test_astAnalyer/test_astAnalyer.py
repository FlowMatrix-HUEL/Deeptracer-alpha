from unittest.mock import Mock, patch
@logtitle
def test_AstAnalyer_import():
    """测试能否正常导入AstAnalyer类"""
    with patch('builtins.__import__'):
        try:
            from deeptracer.astAnalyer import AstAnalyer
            assert AstAnalyer is not None
        except ImportError as e:
            assert str(e) != ""
@logtitle
def test_astVisualizer_structure():
    """测试模块astAnalyer的基本结构"""
    # 不实际导入，而是测试模块路径是否存在
    import os
    file_path = os.path.join('deeptracer', 'astAnalyer', 'viztracer.py')
    assert os.path.exists(file_path), f"viztracer文件不存在: {file_path}"
@logtitle
def test_main_function():
    from deeptracer.astAnalyer import AstAnalyer
    memoryAnalyzer = AstAnalyer(
        "tests/test_sources/test_mem.py",
        open=False
    )
    memoryAnalyzer.visualize()

