import os
import sys
from typing import Optional
from pyinstrument import Profiler
from pyinstrument.renderers import HTMLRenderer
from deeptracer import (
    DEEPTRACER_DEV_ROOT,
    print_color)
class SpeedAnalyzer:
    """
    PyInstrument 性能分析

    """   
    def _validate_py_file(self, 
                          py_file_path: str) -> str:
        """
        校验传入的 py 文件路径合法性
        Args:
            param py_file_path: 用户传入的 py 文件路径
        Returns: 
            规范化的绝对路径
        """
        # 转为绝对路径，处理相对路径问题
        abs_py_path = os.path.abspath(py_file_path)

        # 检查文件是否存在
        if not os.path.exists(abs_py_path):
            raise FileNotFoundError(f"指定的 Python 文件不存在：{abs_py_path}")

        # 检查是否是 .py 文件
        if not abs_py_path.endswith(".py"):
            raise ValueError(f"指定的文件不是 Python 文件(.py):{abs_py_path}")

        # 检查文件是否可读
        if not os.access(abs_py_path, os.R_OK):
            raise PermissionError(f"无读取权限：{abs_py_path}")

        return abs_py_path

    def _execute_py_file(self,
                         py_file_path: str
                         )->None:
        """
        通用执行 py 文件的方法
        Args:
            py_file_path: 规范化的 py 文件绝对路径
        Returns:
            None
        """
        py_dir = os.path.dirname(py_file_path)
        sys.path.insert(0, py_dir)
        try:
            # 读取并执行 py 文件内容
            with open(py_file_path, "r", encoding="utf-8") as f:
                py_code = f.read()

            # 构建执行环境
            exec_globals = {
                "__file__": py_file_path,
                "__name__": "__main__",
                "__package__": None,
                "__cached__": None,
            }
            exec(py_code, exec_globals)
        finally:
            # 移除临时加入的路径
            if sys.path and sys.path[0] == py_dir:
                sys.path.pop(0)
        
    def generate_perf_report(
        self,
        py_file_path: str,
        interval: float = 0.001
    ) -> str:
        """
        核心方法：执行 py 文件并生成 HTML 性能报告
        Args:
            py_file_path: 待分析的 Python 文件路径（相对/绝对）
            interval: 采样间隔（秒），越小精度越高，默认 1ms
        Returns:
            最终生成的 HTML
        """
        abs_py_path = self._validate_py_file(py_file_path)

        
        # 初始化 PyInstrument 分析器
        profiler = Profiler(
            interval=interval
        )

        try:
            # 开始追踪并执行目标 py 文件
            print_color(f"开始分析文件：{abs_py_path}", color="blue")
            profiler.start()
            # 执行 py 文件
            self._execute_py_file(abs_py_path)
            profiler.stop()
            print_color("分析完成，开始生成 HTML 报告...", color="green")

            # 生成 HTML 报告并保存
            renderer = HTMLRenderer()
            html_content = renderer.render(profiler.last_session)
            print_color("HTML 性能报告已生成", color="green")
            return html_content

        except Exception as e:
            raise RuntimeError(f"生成报告失败：{str(e)}") from e
