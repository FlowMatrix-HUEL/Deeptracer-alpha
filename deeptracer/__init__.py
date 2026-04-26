import os
import sys
import platform
import subprocess


def _is_color_supported() -> bool:
    """
    检测当前环境是否支持颜色输出
    
    Args:
        None
    Returns:
        result(bool): 判断是否支持颜色输出
    """
    # 非交互式终端直接不支持
    if not sys.stdout.isatty():
        return False
    
    # Windows系统处理
    if sys.platform.startswith("win"):
        try:
            # 获取Windows版本号
            win_version = platform.version()
            major, _, build = map(int, win_version.split("."))
            if not (major >= 10 and build >= 10586):
                return False
            from ctypes import windll, WinError
            # 主动开启Windows终端ANSI支持
            kernel32 = windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            if handle != 0:
                kernel32.SetConsoleMode(handle, 7)
            return True
        # 明确捕获可能的异常类型 避免吞掉关键错误
        except (ValueError, AttributeError, WinError, OSError):
            return False
    # Linux/macOS 系统处理
    else:
        try:
            # 检测颜色支持
            result = subprocess.check_output(
                ["tput", "colors"], 
                stderr=subprocess.DEVNULL,
                text=True
            )
            color_count = int(result.strip())
            return color_count >= 8
        # 明确捕获 tput 相关异常
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return False 
        
color_support = _is_color_supported()
def print_color(text:str,
                fore_color:str=None,
                back_color:str=None,
                bold:bool=False,
                underline:bool=False)->None:
    """
    带颜色打印函数
    Args:
        text(str): 要输出的文本
        fore_color(str): 前景色
            {"black","red","green","yellow",
            "blue","purple","cyan","white"}
        back_color(str): 背景色
        bold(bool)->Flase: 是否加粗默
        underline(bool)->False: 是否下划线
    
    Returns:
        None
        
    "本函数只支持 linux,macos,window10+ 使用"
    """
    if not color_support:
        # 不支持颜色，直接输出原始文本
        print(text)
        return
    
    # 颜色映射表
    color_map = {
        "black": 0, "red": 1, "green": 2, "yellow": 3,
        "blue": 4, "purple": 5, "cyan": 6, "white": 7
    }
    # 初始化样式列表
    styles = []
    if bold:
        styles.append("1")
    if underline:
        styles.append("4")
    # 前景色（30+颜色编码）
    if fore_color in color_map:
        styles.append(str(30 + color_map[fore_color]))
    # 背景色（40+颜色编码）
    if back_color in color_map:
        styles.append(str(40 + color_map[back_color]))
    # 拼接ANSI序列
    style_str = ";".join(styles) if styles else "0"
    print(f"\033[{style_str}m{text}\033[0m")

def get_deeptracer_root():
    """
    获取deeptracer库的绝对根路径

    Args:
        None
    Returns:
        deeptracer_root(str):绝对路径
    """
    # 1. 获取当前文件（__init__.py）的绝对路径
    current_file = os.path.abspath(__file__)
    # 2. 向上级目录找（__init__.py在deeptracer/下，所以dirname一次就是根）
    deeptracer_root = os.path.dirname(current_file)
    return deeptracer_root

# 定义全局的根路径常量（方便其他模块调用）
DEEPTRACER_ROOT = get_deeptracer_root()
DEEPTRACER_DEV_ROOT = os.path.dirname(DEEPTRACER_ROOT)
#print(DEEPTRACER_DEV_ROOT)
__all__ = [
    "is_color_supported",
    "print_color",
    "get_deeptracer_root",
    "DEEPTRACER_ROOT",
    "DEEPTRACER_DEV_ROOT"
]