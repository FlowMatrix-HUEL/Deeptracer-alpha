# Tracer

\- This project is inspired by UC Berkeley's CS61A course\.

\- It provides a`tracer` decorator and a `Tracer` context manager to track function invocation behaviors\.

---

## Getting Started with Tracer

You can clone the Tracer repository from GitHub:

```bash
git clone https://github.com/Ricardo-shuo-liu/Tracer.git

cd Tracer

# Activate your virtual environment
conda activate yourEnv
# Conda is for demonstration; you can also use uv or venv

pip install -e .
```

Alternatively, install directly via PyPI:

```bash
conda activate yourEnv

pip install pypi-tracer
```

\- **Note**: The PyPI package is named `pypi-tracer` due to PyPI naming uniqueness restrictions\.

\- However, the top\-level import package name is `tracer`\.

## Using the `tracer` Decorator

Refer to `tests/core/test_tracer.py` for demonstration code:

```python
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

Execution output:

```Plain Text
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

## Using the `Tracer` Context Manager

Refer to `tests/core/test_Tracer.py` for demonstration code:

```python
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

Execution output:

```Plain Text
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

**Important Note**: The `Tracer` context manager does not provide the `trace_entity: bool` interface\.

## Core Features of Tracer

---

### 1\. Logging Functionality

- Built on Python's native `logging` module

- Enabled via the `logging_path` parameter of both `tracer` decorator and `Tracer` context manager

- `logging_path` defaults to `None`\. A valid file path will enable log file storage at the specified location

See `tests/core/test_log_tracer.py` and `tests/core/test_log_Tracer.py` for usage examples\.

### 2\. Time Tracing

- Built on Python's `time` and `dataclass` modules

- Implements unique record tracking via frame identification

- Enabled via the `time_trace` parameter of `tracer` and `Tracer`

- `time_trace` defaults to `False`; set to `True` to activate time tracing

Example:

```python
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

Output:

```Plain Text
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

Refer to `tests/core/test_time_Tracer.py` for time tracing usage with the `Tracer` context manager\.

### 3\. Initial Interactive Inspection

- Built on Python's `code.interact` module

- Enabled via the `interactive: bool` parameter

- Activates a shell interactive session to inspect runtime data

Example:

```python
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

Runtime output:

```Plain Text
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

The `Tracer` context manager also supports this parameter\. See `tests/interact/test_Tracer_interact.py` for usage examples\.

### 4\. Terminal Interaction at Key Events

- Built on Python's `code.interact` module

- Enabled via the `interactive_on_event: bool` parameter

- Triggers shell interaction at key runtime nodes for data inspection

Example:

```python
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

Runtime output:

```Plain Text
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

Enabling `interactive_on_event: bool` triggers interactive sessions at both function entry and return events for traced functions\.

The `Tracer` context manager supports this parameter as well\. See `tests/interact/test_Tracer_interact_on_event.py` for details\.

**Important Warning**: Enabling `interactive_on_event: bool` is generally not recommended\. It requires handling exceptions including `SystemExit`, `EOFError`, and `ValueError` to avoid program termination\. Additionally, it triggers two interactive sessions per function call, which is inefficient for large\-scale program execution\. Enable this feature only if you fully understand its behavior and have specific debugging needs\.

### 5\. Selective Terminal Interaction at Key Nodes

- Built on Python's`code.interact` module

- Enabled via the `interactive_filter: List[Callable] | None` parameter

- Triggers targeted shell interactive sessions for precise runtime inspection

- `interactive_filter` defaults to `None`, meaning no selective interaction nodes are enabled

- When configured, it must be a subset of the functions defined in `trace_fn`

- Co\-usage with `interactive_on_event: bool` yields the same effect as enabling only `interactive_on_event`

- Provides finer\-grained control than `interactive_on_event` and is thus the recommended interactive debugging mode

Example:

```python
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

Runtime output:

```Plain Text
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

Refer to `tests/interact/test_Tracer_interactive_filter.py` for usage with the `Tracer` context manager\.

### 6\. Color Rendering

- Built on Python's `sys`, `platform`, and `subprocess` modules

- Enabled via the `use_color: bool` parameter

- No invalid character output on operating systems that do not support colored terminal output

- Only core tracing content is color\-formatted; full terminal output is not modified

- **Note**: Enabling color rendering will cause garbled characters in log files due to string splicing\. It is recommended to disable logging when using color output\.

See `tests/core/test_tracer_color.py` for color rendering effects with the `tracer` decorator, and `tests/core/test_Tracer_color.py` for the `Tracer` context manager\.

### 7\. Exception Extraction

- Built on Python's `traceback`, `dataclasses` and `json` modules

- Enabled via the `exception_trace: bool` parameter of both `tracer` decorator and `Tracer` context manager

- Captures every exception raised inside the traced scope and prints a structured report after execution

- **A function that unwinds because of an exception prints `raised` instead of `returned None`**, so failures
  are no longer indistinguishable from a legitimate `None` return value

Example:

```python
from tracer import tracer

def deep_untraced(n):          # NOT passed to trace_fn
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

Runtime output:

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

What gets extracted for every exception:

| Field | Meaning |
| --- | --- |
| `exc_type` / `message` | Exception class name and `str()` of the instance |
| `raised at` | Real raise point: function, file and line number |
| `stack` | Full traceback chain **including frames that were never traced** |
| `propagated` | Traced functions the exception travelled through, e\.g\. `dive x4 -> safe` |
| `status` | `handled by xxx()` when swallowed inside the scope, `escaped` otherwise |
| `locals` | Local variable snapshot at the observation point, only when `show_locals=True` |

Related parameters:

- `exception_trace: bool = False` — master switch for exception extraction

- `show_locals: bool = False` — snapshot local variables where the exception is first observed

- `exception_json_path: str | None = None` — dump all records to a JSON file after execution

Programmatic access:

```python
with Tracer(trace_fn=[dive], exception_trace=True) as t:
    ...
t.errors.records        # list[ExcRecord]
t.errors.to_list()      # list[dict], JSON-serialisable
t.errors.unhandled      # exceptions that escaped the traced scope
```

With the decorator, the live context hangs off the wrapper:

```python
@tracer(trace_entity=True, exception_trace=True)
def run(): ...

run()
run.tracer_ctx.errors.to_list()
```

**Important Note**: Exceptions are only observed inside frames that match `trace_fn` / `trace_entity`\.
Tracer never swallows or suppresses anything — the exception keeps propagating exactly as before\.

See `tests/core/test_exception_tracer.py` for the decorator flavour and
`tests/core/test_Tracer_exception.py` for the context manager flavour\.
