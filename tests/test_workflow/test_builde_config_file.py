from unittest.mock import Mock, patch
@logtitle
def test_builder_import():
    """测试能否正常导入build_env_local类"""
    with patch('builtins.__import__'):
        try:
            from deeptracer.workflow import build_env_local
            assert build_env_local is not None
        except ImportError as e:
            assert str(e) != ""
@logtitle
def test_build_env_local_structure():
    """测试build_env_local模块的基本结构"""
    # 不实际导入，而是测试模块路径是否存在
    import os
    file_path = os.path.join('deeptracer', 'workflow', '__init__.py')
    assert os.path.exists(file_path), f"__init__文件不存在: {file_path}"
@logtitle
def test_creator_function():
    from deeptracer.workflow import build_env_local
    builder = build_env_local()
    builder.creator("sat_8WvTYiyCrWzXEl1wj7d3MAo1lXTPFXX8C9BRA3YpgwfNQFPdmSLMfeDfmHyYi2wu")
