from tracer import tracer

def add(x,y):
    return x + y


def chain(n):
    if n <= 1:
        return add(1,1)
    return add(n, chain(n-1))

@tracer(trace_fn=[add, chain],
        trace_entity=True,
        logging_path="/home/ricaedo/Tracer/test.log",
        interactive_filter=[add])
def fun():
    return chain(3)

@tracer(trace_entity=True,
        logging_path="/home/ricaedo/Tracer/test.log",
        interactive_on_event=True)
def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-2) + fib(n-1)
if __name__ == "__main__":
    fun()
