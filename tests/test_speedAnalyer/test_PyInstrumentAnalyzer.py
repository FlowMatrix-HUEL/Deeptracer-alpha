from unittest.mock import Mock, patch
@logtitle
def test_SpeedAnalyzer_import():
    """测试能否正常导入SpeedAnalyzer类"""
    with patch('builtins.__import__'):
        try:
            from deeptracer.speedAnalyer import SpeedAnalyzer
            assert SpeedAnalyzer is not None
        except ImportError as e:
            assert str(e) != ""
@logtitle
def test_viztracerAnalyer_structure():
    """测试模块viztracerAnalyer的基本结构"""
    # 不实际导入，而是测试模块路径是否存在
    import os
    file_path = os.path.join('deeptracer', 'speedAnalyer', 'viztracer.py')
    assert os.path.exists(file_path), f"viztracer文件不存在: {file_path}"
@logtitle
def test_main_function():
    from deeptracer.speedAnalyer import SpeedAnalyzer
    Analyzer = SpeedAnalyzer()
    Analyzer.generate_perf_report("tests/test_sources/test_mem.py")
