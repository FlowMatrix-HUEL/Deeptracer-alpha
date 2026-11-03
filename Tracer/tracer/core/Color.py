from enum import Enum
import sys
import platform
import subprocess

class Colors(Enum):
    """ANSI color codes for terminal output"""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    BLACK = '\033[30m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    NC = "\033[0m"  # No Color

def _is_color_supported() -> bool:
    """
    Detect whether the current environment supports color output

    Args:
        None
    Returns:
        result(bool): Whether color output is supported
    """
     # Non-interactive terminals do not support color output
    if not sys.stdout.isatty():
        return False
    
    # Handle Windows systems
    if sys.platform.startswith("win"):
        try:
            # Get Windows version number
            win_version = platform.version()
            major, _, build = map(int, win_version.split("."))
            if not (major >= 10 and build >= 10586):
                return False
            from ctypes import windll
            # Actively enable ANSI support for Windows terminal
            INVALID_HANDLE_VALUE = -1
            kernel32 = windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE       
            if handle == INVALID_HANDLE_VALUE:
                return False
            success = kernel32.SetConsoleMode(handle, 7)
            return bool(success)
        except BaseException as e:
            if isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise e
            return False
    # Handle Linux/macOS systems
    else:
        try:
            # Detect color support
            result = subprocess.check_output(
                ["tput", "colors"], 
                stderr=subprocess.DEVNULL,
                text=True
            )
            color_count = int(result.strip())
            return color_count >= 8
        # Explicitly catch tput-related exceptions
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return False 
        
COLOR_SUPPORT = _is_color_supported()

def set_color(s: str,
              color: str) -> str:
    """
    Wrap input string with specified ANSI terminal color escape sequence.
    Color name argument is case-insensitive. If color is unsupported or invalid,
    returns original raw string without any escape codes.

    Args:
        s: Original text string to be colored
        color: Color enum name, case-insensitive (e.g. "red", "GREEN", "Yellow")
    Returns:
        str: Text wrapped with ANSI color codes if color output is available,
             otherwise the unmodified input string
    Examples:
        >>> set_color(s="hello world",color="red")

    """
    
    if COLOR_SUPPORT:
        return f"{getattr(Colors, color.strip().upper()).value}{s}{Colors.NC.value}"
    return f"{s}"  # pragma: no cover