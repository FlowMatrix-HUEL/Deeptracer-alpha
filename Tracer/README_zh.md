# Tracer

- 本项目灵感来自UC伯克利的课程CS61A 

- 使用`tracer`装饰器和`Tracer`上下文管理器来追踪函数的调用情况

---
### 开始使用Tracer

你可通过clone `Tracer`的Github仓库
```
git clone https://github.com/Ricardo-shuo-liu/Tracer.git

cd Tracer

# 启动你的环境
conda activate yourEnv
# 这里只是示范 你当然可以选择uv或者venv

pip install -e .
```

或者通过`Pypi`直接下载 

```
conda activate yourEnv

pip install pypi-tracer
```

- 这里需要说明的是`pip`下载的项目名称为`pypi-tracer`因为`pypi`不允许重名
- 但是在导入的时候 最高级包为`tracer`


### 使用`tracer`装饰器

- 你可以查看`tests\core\test_tracer.py`内容
```
from tracer import tracer

def add(x,y):
    return x + y


def chain(n):
    if n <= 1:
        return add(1,1)
    return add(n, chain(n-1))

@tracer(trace_fn=[add, chain],
        trace_entity=True)
def fun():
    return chain(3)

@tracer(trace_entity=True)
def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-2) + fib(n-1)
if __name__ == "__main__":
    fun()
    print()
    fib(3)
```
执行结果如下:
```
-> fun()
|  -> chain(n=3)
|  |  -> chain(n=2)
|  |  |  -> chain(n=1)
|  |  |  |  -> add(x=1, y=1)
|  |  |  |  |  <- add returned 2
|  |  |  |  <- chain returned 2
|  |  |  -> add(x=2, y=2)
|  |  |  |  <- add returned 4
|  |  |  <- chain returned 4
|  |  -> add(x=3, y=4)
|  |  |  <- add returned 7
|  |  <- chain returned 7
|  <- fun returned 7

-> fib(n=3)
|  -> fib(n=1)
|  |  <- fib returned 1
|  -> fib(n=2)
|  |  -> fib(n=0)
|  |  |  <- fib returned 0
|  |  -> fib(n=1)
|  |  |  <- fib returned 1
|  |  <- fib returned 1
|  <- fib returned 2
```

### 使用`Tracer`上下文管理器

- 你可以查看`tests\core\test_Tracer.py`内容
```
from tracer import Tracer


def add(x,y):
    return x + y


def chain(n):
    if n <= 1:
        return add(1,1)
    return add(n, chain(n-1))

def fun():
    return chain(3)

def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-2) + fib(n-1)
    
if __name__ == "__main__":
    with Tracer(trace_fn=[add,chain,fun,fib]):
        fun()
        print()
        fib(3)
```
执行结果如下：
```
-> fun()
|  -> chain(n=3)
|  |  -> chain(n=2)
|  |  |  -> chain(n=1)
|  |  |  |  -> add(x=1, y=1)
|  |  |  |  |  <- add returned 2
|  |  |  |  <- chain returned 2
|  |  |  -> add(x=2, y=2)
|  |  |  |  <- add returned 4
|  |  |  <- chain returned 4
|  |  -> add(x=3, y=4)
|  |  |  <- add returned 7
|  |  <- chain returned 7
|  <- fun returned 7

-> fib(n=3)
|  -> fib(n=1)
|  |  <- fib returned 1
|  -> fib(n=2)
|  |  -> fib(n=0)
|  |  |  <- fib returned 0
|  |  -> fib(n=1)
|  |  |  <- fib returned 1
|  |  <- fib returned 1
|  <- fib returned 2
```

需要注意的是`Tracer`上下文管理器没有提供`trace_entity：bool`接口

### Tracer的设计功能
---
1. 日志功能

- 基于`logging`模块 
- 通过`tracer`和`Tracer`的`logging_path`实现启用
- `logging_path` 默认数值为 `None` 如果传入真实地址 那么认为该真实地址为log的存储位置

你可以查询 `tests/core/test_log_tracer.py` 和 `tests/core/test_log_Tracer.py` 了解如何使用
---
2. 时间追踪

- 基于`time` 和 `dataclass` 模块
- 通过标识`frame`实现唯一纪律
- 通过`tracer`和`Tracer`的`time_trace`实现启用
- `time_trace` 默认数值为 `False` 修改为`True` 认为是启用

Example:
```
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
        time_trace=True)
def fun():
    return chain(3)

@tracer(trace_entity=True,logging_path="/home/ricaedo/Tracer/test.log",time_trace=True)
def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-2) + fib(n-1)
if __name__ == "__main__":
    fun()
    print()
    fib(3)
```
输出:
```
-> fun()
|  -> chain(n=3)
|  |  -> chain(n=2)
|  |  |  -> chain(n=1)
|  |  |  |  -> add(x=1, y=1)
|  |  |  |  |  <- add returned 2 | cost=0.000013s
|  |  |  |  <- chain returned 2 | cost=0.000042s
|  |  |  -> add(x=2, y=2)
|  |  |  |  <- add returned 4 | cost=0.000012s
|  |  |  <- chain returned 4 | cost=0.000092s
|  |  -> add(x=3, y=4)
|  |  |  <- add returned 7 | cost=0.000012s
|  |  <- chain returned 7 | cost=0.000150s
|  <- fun returned 7 | cost=0.000223s

===== Function Trace Statistics Report =====
Function        Calls   Total(s)  Avg(s)    Min(s)    Max(s)    
add             3       0.0000    0.0000    0.0000    0.0000    
chain           3       0.0003    0.0001    0.0000    0.0001    
fun             1       0.0002    0.0002    0.0002    0.0002    
============================================


-> fib(n=3)
|  -> fib(n=1)
|  |  <- fib returned 1 | cost=0.000012s
|  -> fib(n=2)
|  |  -> fib(n=0)
|  |  |  <- fib returned 0 | cost=0.000011s
|  |  -> fib(n=1)
|  |  |  <- fib returned 1 | cost=0.000011s
|  |  <- fib returned 1 | cost=0.000059s
|  <- fib returned 2 | cost=0.000115s

===== Function Trace Statistics Report =====
Function        Calls   Total(s)  Avg(s)    Min(s)    Max(s)    
fib             5       0.0002    0.0000    0.0000    0.0001    
============================================
```
关于上下文管理器`Tracer`启用相关功能可以查看`tests/core/test_time_Tracer.py`

3. 开始时的交互式检查

- 基于`code.interact` 模块
- 通过 `interactive:bool`启用
- 启用后会进入`shell`交互可以查看数据内容

Example:
```
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
        interactive=True)
def fun():
    return chain(3)

@tracer(trace_entity=True,
        logging_path="/home/ricaedo/Tracer/test.log",
        interactive=True)
def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-2) + fib(n-1)
if __name__ == "__main__":
    fun()
    print()
    fib(3)
```
运行结果:
```
==== Tracer Interactive Shell ====

===+fun()+===

>>> exit()

[Tracer] Interactive exit: SystemExit

-> fun()
|  -> chain(n=3)
|  |  -> chain(n=2)
|  |  |  -> chain(n=1)
|  |  |  |  -> add(x=1, y=1)
|  |  |  |  |  <- add returned 2
|  |  |  |  <- chain returned 2
|  |  |  -> add(x=2, y=2)
|  |  |  |  <- add returned 4
|  |  |  <- chain returned 4
|  |  -> add(x=3, y=4)
|  |  |  <- add returned 7
|  |  <- chain returned 7
|  <- fun returned 7


==== Tracer Interactive Shell ====

===+fib(3)+===

>>> exit()

[Tracer] Interactive exit: SystemExit
3
-> fib(n=3)
|  -> fib(n=1)
|  |  <- fib returned 1
|  -> fib(n=2)
|  |  -> fib(n=0)
|  |  |  <- fib returned 0
|  |  -> fib(n=1)
|  |  |  <- fib returned 1
|  |  <- fib returned 1
|  <- fib returned 2
```

当然在`Tracer`上下文管理器也支持该参数
你可以访问`tests/interact/test_Tracer_interact.py`查看使用示范

4. 关键节点启动终端交互

- 基于`code.interact` 模块
- 通过 `interactive_on_event:bool`启用
- 启用后会进入`shell`交互可以查看数据内容

Example:

```
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
        interactive_on_event=True)
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
    fib(2)

```
运行结果:

```
==== Tracer Interactive Shell ====

===+fib(n=2)+===

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+fib(n=0)+===

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+fib returned 0====

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+fib(n=1)+===

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+fib returned 1====

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+fib returned 1====

>>> exit()

[Tracer] Interactive exit: SystemExit
-> fib(n=2)
|  -> fib(n=0)
|  |  <- fib returned 0
|  -> fib(n=1)
|  |  <- fib returned 1
|  <- fib returned 1
```

启动`interactive_on_event:bool`后会在追踪函数的开始和`Return`时候启动交互式

当然在`Tracer`也支持这个参数
你可以查看`tests/interact/test_Tracer_interact_on_event.py`了解相关的example

- 需要注意的是！一般情况下,并不建议开启`interactive_on_event:bool`,因为对于终端的保存,必须要屏蔽`SystemExit` `EOFError` `ValueError` 这些Error可能导致停止程序只能通过销毁终端的方式,而且由于每个函数近乎需要进入两次交互,在大规模的情况下这可能不是一个好的选择

- 你必须知道你要干什么,否则不建议启用`interactive_on_event:bool`

5. 关键节点选择性终端交互

- 基于`code.interact` 模块
- 通过 `interactive_filter:List[Callable]|None`启用
- 启用后会进入`shell`交互可以查看数据内容
- `interactive_filter:List[Callable]|None`默认数值为`None` 此时认为没有选者的节点
- `interactive_filter:List[Callable]|None` 如果设置应该为`trace_fn`的子集
- `interactive_filter:List[Callable]|None` 可以和 `interactive_on_event:bool`共用 这个时候实际效果和只启动`interactive_on_event:bool`是一样的
- 相较于`interactive_on_event:bool`的深度的追踪`interactive_filter:List[Callable]|None`能做到更精细的控制 所以更推荐使用`interactive_filter:List[Callable]|None`

Example:
```
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
        use_color=True)
def fun():
    return chain(3)

@tracer(trace_entity=True,
        logging_path="/home/ricaedo/Tracer/test.log",
        use_color=True,
        time_trace=True)
def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-2) + fib(n-1)
if __name__ == "__main__":
    fun()
    print()
    fib(3)

```
运行结果:
```
==== Tracer Interactive Shell ====

===+add(x=1, y=1)+===

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+add returned 2====

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+add(x=2, y=2)+===

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+add returned 4====

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+add(x=3, y=4)+===

>>> exit()

[Tracer] Interactive exit: SystemExit

==== Tracer Interactive Shell ====

===+add returned 7====

>>> exit()

[Tracer] Interactive exit: SystemExit
-> fun()
|  -> chain(n=3)
|  |  -> chain(n=2)
|  |  |  -> chain(n=1)
|  |  |  |  -> add(x=1, y=1)
|  |  |  |  |  <- add returned 2
|  |  |  |  <- chain returned 2
|  |  |  -> add(x=2, y=2)
|  |  |  |  <- add returned 4
|  |  |  <- chain returned 4
|  |  -> add(x=3, y=4)
|  |  |  <- add returned 7
|  |  <- chain returned 7
|  <- fun returned 7
```

对于上下文管理器`Tracer`可以查看`tests/interact/test_Tracer_interactive_filter.py`了解如何使用

6. 色彩修正

- 基于模块`sys` `platform` `subprocess`实现
- 通过`use_color:bool`启动
- 对于部分不支持色彩输出的操作系统 如果启动`use_color`不会有任何效果(乱码屏蔽)
- 色彩修正是对部分核心内容进行色彩处理 而不是终端的所有内容都会被色彩修正
- 需要注意如果启动色彩修正 那么`log`存储的内容中会出现乱码 这是字符串拼接的原因 所以最好关闭`log`

对于`tracer`装饰器 运行`tests/core/test_tracer_color.py`了解效果和使用方法
对于`Tracer`上下文管理器 运行`tests/core/test_Tracer_color.py`了解效果和使用方法
### 7\. 异常提取

- 基于 Python 标准库 `traceback`、`dataclasses`、`json` 实现

- 通过 `tracer` 装饰器与 `Tracer` 上下文管理器的 `exception_trace: bool` 参数开启

- 捕获被追踪作用域内抛出的每一个异常，并在执行结束后输出结构化报告

- **因异常退出的函数会打印 `raised` 而不是 `returned None`**，修复了"异常退出"与"正常返回 None"无法区分的问题

示例：

```python
from tracer import tracer

def deep_untraced(n):          # 未加入 trace_fn
    if n < 0:
        raise ValueError(f"negative depth: {n}")
    return n * 2

def risky(n):
    return deep_untraced(n)

def swallowed():
    try:
        raise KeyError("swallowed_key")
    except KeyError:
        return "recovered"

@tracer(trace_fn=[risky, swallowed],
        trace_entity=True,
        exception_trace=True,
        show_locals=True)
def run():
    swallowed()
    return risky(-1)

if __name__ == "__main__":
    try:
        run()
    except ValueError as e:
        print(f"[outside] caught: {type(e).__name__}: {e}")
```

运行输出：

```Plain Text
-> run()
|  -> swallowed()
|  |  <- swallowed returned 'recovered'
|  -> risky(n=-1)
|  |  <- risky raised ValueError: negative depth: -1
|  <- run raised ValueError: negative depth: -1

===== Exception Trace Report =====
total=2  unhandled=1  handled=1  by_type={'KeyError': 1, 'ValueError': 1}
----------------------------------
#1  KeyError: 'swallowed_key'
    status      : handled by swallowed()
    raised at   : swallowed() -> demo.py:13
    propagated  : swallowed
    stack (outermost -> raise point):
      File "demo.py", line 13, in swallowed
        raise KeyError("swallowed_key")
----------------------------------
#2  ValueError: negative depth: -1
    status      : escaped (unhandled within traced scope)
    raised at   : deep_untraced() -> demo.py:5
    propagated  : risky -> run
    stack (outermost -> raise point):
      File "demo.py", line 20, in run
        return risky(-1)
      File "demo.py", line 8, in risky
        return deep_untraced(n)
      File "demo.py", line 5, in deep_untraced
        raise ValueError(f"negative depth: {n}")
    locals at observation point:
      n = -1
----------------------------------
==================================
```

每个异常被提取的字段：

| 字段 | 含义 |
| --- | --- |
| `exc_type` / `message` | 异常类名与实例的 `str()` |
| `raised at` | 真实抛出点：函数名、文件、行号 |
| `stack` | 完整 traceback 链，**包含从未被追踪的中间帧** |
| `propagated` | 异常流经的被追踪函数，例如 `dive x4 -> safe` |
| `status` | 被作用域内捕获显示 `handled by xxx()`，否则显示 `escaped` |
| `locals` | 观测点的局部变量快照，仅在 `show_locals=True` 时采集 |

相关参数：

- `exception_trace: bool = False` —— 异常提取总开关

- `show_locals: bool = False` —— 采集异常首次被观测处的局部变量

- `exception_json_path: str | None = None` —— 执行结束后将记录导出为 JSON 文件

程序化访问：

```python
with Tracer(trace_fn=[dive], exception_trace=True) as t:
    ...
t.errors.records        # list[ExcRecord]
t.errors.to_list()      # list[dict]，可直接序列化
t.errors.unhandled      # 逃出追踪作用域的异常
```

装饰器版本通过包装函数暴露上下文对象：

```python
@tracer(trace_entity=True, exception_trace=True)
def run(): ...

run()
run.tracer_ctx.errors.to_list()
```

**重要说明**：只有在 `trace_fn` / `trace_entity` 命中的帧内才会观测到异常\.
Tracer 不会吞掉或抑制任何异常，异常依旧按原路径向上传播\.

装饰器用法参见 `tests/core/test_exception_tracer.py`，上下文管理器用法参见
`tests/core/test_Tracer_exception.py`\.
