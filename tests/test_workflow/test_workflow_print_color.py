from deeptracer import print_color
@logtitle
def test_print_color():
    # 测试print_color函数是否能正常工作
    try:
        print_color("This will print a red string if your system is Ok",fore_color="red")
        # 如果没有抛出异常，则测试通过
        assert True
    except Exception as e:
        # 如果抛出异常，则测试失败
        assert False, f"print_color函数执行出错: {e}"