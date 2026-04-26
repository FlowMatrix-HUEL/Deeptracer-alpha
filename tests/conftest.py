import logging
import functools
import os
from typing import Callable
from pathlib import Path
import pytest

logger_cache = {}

def get_target_path():
    """
    获得当Deeptracer文件夹所处路径
    """
    target_path = Path(__file__).resolve().parent.parent

    return target_path
def logtitle(func:Callable
             )->Callable:
    """
    测试文档记录->自动记录测试文档
    Args:
        func(Callable):装饰器函数
    Returns:
        tools(Callable):装饰后的函数
    """
    logger_name = func.__module__
    @functools.wraps(func)
    def tools(*args,**kwargs):
        if logger_name not in logger_cache:
            log = logging.getLogger(logger_name)
            log.setLevel(logging.DEBUG)
            log.propagate = False 
            log.handlers.clear()  
            
            
            log_file = os.path.join(get_target_path(), "test.logs")
            logFiler = logging.FileHandler(log_file, encoding="utf-8")
            logFiler.setLevel(logging.ERROR)  # 只记录错误日志

            # 配置控制台处理器
            loghandler = logging.StreamHandler()
            loghandler.setLevel(logging.INFO)

            # 日志格式：包含时间、级别、函数名、信息
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
            loghandler.setFormatter(formatter)
            logFiler.setFormatter(formatter)

            # 添加处理器并缓存
            log.addHandler(logFiler)
            log.addHandler(loghandler)
            logger_cache[logger_name] = log
        else:
            log = logger_cache[logger_name]

        try:
            # 执行测试函数
            result = func(*args, **kwargs)
            log.info(f"测试用例 {func.__name__} 执行完成（无业务异常）")
            return result

        except Exception as e:
            # 记录业务异常日志
            log.error(f"测试用例 {func.__name__} 业务执行失败", exc_info=True)
            raise e  # 重新抛出，让pytest标记测试失败
        # 系统级异常直接放行，不记录日志
        except BaseException as e:
            # 控制台打印提示
            log.info(f"测试用例 {func.__name__} 触发系统级异常（非业务错误）: {type(e).__name__}")
            raise e  # 直接抛出，不记录到test.log
        finally:
            # 刷新缓冲区，确保日志写入文件
            for handler in log.handlers:
                handler.flush()

    return tools
def pytest_configure(config):
    import builtins
    builtins.logtitle = logtitle
