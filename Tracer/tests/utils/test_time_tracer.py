def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-2) + fib(n-1)


from tracer.utils import time_tracer

res = time_tracer(target=fib,args=(3,))
print(res)