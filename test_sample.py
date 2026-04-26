"""
示例 Python 文件 - 用于测试 DeepTracer 的文件选择功能
"""

def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b


def factorial(n):
    """计算阶乘"""
    if n < 0:
        raise ValueError("n 必须是非负整数")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def main():
    print("=== DeepTracer 文件选择功能测试 ===")
    
    # 测试斐波那契数列
    print("\n斐波那契数列前 10 项：")
    for i in range(10):
        print(f"F({i}) = {fibonacci(i)}")
    
    # 测试阶乘
    print("\n前 5 个数的阶乘：")
    for i in range(6):
        print(f"{i}! = {factorial(i)}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()
