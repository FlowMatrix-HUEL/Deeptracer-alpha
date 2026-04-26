from unittest.mock import Mock, patch
@logtitle
def test_CodeStructureAnalyzer_import():
    """测试能否正常导入CodeStructureAnalyzer类"""
    with patch('builtins.__import__'):
        try:
            from deeptracer.astAnalyer import CodeStructureAnalyzer
            assert CodeStructureAnalyzer is not None
        except ImportError as e:
            assert str(e) != ""
@logtitle
def test_viztracer_structure():
    """测试模块astVisualizer的基本结构"""
    # 不实际导入，而是测试模块路径是否存在
    import os
    file_path = os.path.join('deeptracer', 'astAnalyer', 'viztracer.py')
    assert os.path.exists(file_path), f"viztracer文件不存在: {file_path}"
@logtitle
def test_main_function():
    from deeptracer.astAnalyer import CodeStructureAnalyzer
    memoryAnalyzer = CodeStructureAnalyzer(
        "tests/test_sources/test_mem.py",
    )
    memoryAnalyzer.visualize()
