import code


def interact_continue(namespace):
    try:
        code.interact(local=dict(globals(), **locals()))
    except SystemExit:
        # 捕获exit触发的退出异常，不让程序终止
        print("\n===== 退出交互，继续执行程序 =====")



def test(a, b):
    c = a + b
    # 在这里开启交互
    print("1111")
    namespace = {}
    namespace.update(globals())
    namespace.update(locals())
    interact_continue(namespace=namespace)
    print("继续执行，c =", c)

test(10,20)
