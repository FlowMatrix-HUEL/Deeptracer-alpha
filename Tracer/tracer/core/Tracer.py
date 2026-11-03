# Trace.py
import functools
import sys
from typing import Callable, List
from .TraceContext import TraceContext
from .Parser import frame_callback
from .Log import Log
from tracer.interact import SetInteract

def tracer(
        trace_fn: List[Callable] | None = None,
        trace_entity:bool=False,
        logging_path:str | None = None,
        time_trace:bool=False,
        interactive:bool= False,
        interactive_on_event:bool=False,
        interactive_filter:List[Callable]|None = None,
        use_color:bool=False,
        exception_trace:bool=False,
        show_locals:bool=False,
        exception_json_path:str|None=None) -> Callable:
    """
    Decorator to capture function call stack, print hierarchical invocation tree,
    support execution time statistics, exception extraction and interactive debugging.

    Args:
        trace_fn: List of additional target functions to trace. Set None if no extra functions need tracking.
        trace_entity: If True, trace the decorated function itself.
        logging_path: File path for log persistence. If None, logs will only print to console without file output.
        time_trace: Enable runtime statistics. Records invocation count and execution time, and prints summary report after execution completes.
        interactive: If True, launch an interactive Python shell once before tracing starts at the top-level entry.
            Type exit() to resume program execution.
        interactive_on_event: If True, pause and open interactive shell on every call / return event of traced functions.
            WARNING: Reserved for deep debugging only.
            Blocking inside trace callback may lead to unstable tracing. Not recommended for regular use.
        exception_trace: If True, capture every exception raised inside the traced scope, including
            full traceback stack (even frames that are not traced), propagation path across traced
            functions, and whether it was swallowed or escaped. Prints a report after execution.
        show_locals: Only effective when exception_trace=True. Snapshot local variables at the frame
            where the exception was first observed.
        exception_json_path: Only effective when exception_trace=True. Dump the exception records to
            this JSON path after execution. Skipped if None.

    Examples:
        >>> # Basic usage: trace the decorated function and print tree log to console
        >>> @tracer(trace_entity=True)
        >>> def fib(n):
        >>>     if n <= 1:
        >>>         return n
        >>>     return fib(n - 2) + fib(n - 1)

        >>> # Trace self and inner functions, save logs into file
        >>> @tracer(trace_fn=[add, chain], trace_entity=True, logging_path="./trace.log")
        >>> def run():
        >>>     return chain(3)

        >>> # Enable execution time statistics
        >>> @tracer(trace_entity=True, time_trace=True)
        >>> def fib(n):
        >>>     ...

        >>> # Enter interactive shell before tracing starts
        >>> @tracer(trace_entity=True, interactive=True)
        >>> def fib(n):
        >>>     ...

        >>> # Debug mode: pause on each function call / return (debug only)
        >>> @tracer(trace_entity=True, interactive_on_event=True)
        >>> def fib(n):
        >>>     ...
    """
    def include(fn: Callable) -> Callable:
        target_names = set()
        if trace_entity:
            target_names.add(fn.__name__)
        if trace_fn is not None:
            target_names.update(f.__name__ for f in trace_fn)
        target_names = target_names if target_names else None

        filter = set()

        if interactive_filter:
            filter.update(f.__name__ for f in interactive_filter)
        filter = filter if filter else None
        logger = Log(logging_path=logging_path).get_logger() if logging_path else None
       
        ctx = TraceContext(logger=logger,
                           time_trace=time_trace,
                           set_color=use_color,
                           exception_trace=exception_trace,
                           show_locals=show_locals,
                           exception_json_path=exception_json_path)
        @functools.wraps(fn)
        def wrapped(*args, **kwds):
            def hook(frame, event, arg):
                return frame_callback(ctx,
                                      target_names,
                                      interactive_on_event,
                                      filter,
                                      frame,
                                      event,
                                      arg)
            
            depth = getattr(wrapped, "_depth", 0)

            if depth == 0:
                ctx.prefix = ""
                
                if interactive:
                    namespace = {}
                    f = ""
                    for arg in args:
                        f += f"{arg},"
                    for k, v in kwds.items():
                        f += f"{k}={v},"

                    namespace.update(globals())
                    namespace.update(locals())
                    SetInteract(namespace=namespace,
                                func_name=str(fn.__name__),
                                event="call",
                                arg_text=f"{f}"[:-1])
                    print(f"{f}"[:-1])
                sys.settrace(hook)    
            setattr(wrapped, "_depth", depth + 1)
            try:
                return fn(*args, **kwds)
            finally:
                new_depth = getattr(wrapped, "_depth") - 1
                setattr(wrapped, "_depth", new_depth)
                if new_depth == 0:
                    sys.settrace(None)
                    ctx.finish()

        # expose the live context so callers can inspect records programmatically
        wrapped.tracer_ctx = ctx
        return wrapped
    return include

class Tracer:
    def __init__(self,
                 trace_fn: List[Callable] | None = None,
                 logging_path:str|None = None,
                 time_trace:bool=False,
                 interactive:bool= False,
                 interactive_on_event:bool=False,
                 interactive_filter:List[Callable]|None = None,
                 use_color:bool=False,
                 exception_trace:bool=False,
                 show_locals:bool=False,
                 exception_json_path:str|None=None):
        """
        Context manager version of tracing utility, supports `with` syntax.
        Captures function call stack, prints hierarchical invocation tree,
        collects runtime statistics, extracts exceptions and provides interactive debugging.

        Args:
            trace_fn: List of additional target functions to trace. Set None if no extra functions need tracking.
            logging_path: File path for log persistence. If None, logs will only print to console without file output.
            time_trace: Enable runtime statistics. Records invocation count and execution time, and prints summary report after execution completes.
            interactive: If True, launch an interactive Python shell once before tracing starts.
                Type exit() to resume program execution.
            interactive_on_event: If True, pause and open interactive shell on every call / return event of traced functions.
                WARNING: Reserved for deep debugging only.
                Blocking inside trace callback may lead to unstable tracing. Not recommended for regular use.
            exception_trace: If True, capture every exception raised inside the traced scope, including
                full traceback stack (even frames that are not traced), propagation path across traced
                functions, and whether it was swallowed or escaped. Prints a report on exit.
            show_locals: Only effective when exception_trace=True. Snapshot local variables at the frame
                where the exception was first observed.
            exception_json_path: Only effective when exception_trace=True. Dump the exception records to
                this JSON path on exit. Skipped if None.

        Examples:
            >>> def fib(n):
            >>>     if n <= 1:
            >>>         return n
            >>>     return fib(n - 2) + fib(n - 1)

            >>> # Basic usage: trace fib and print call tree
            >>> with Tracer(trace_fn=[fib]):
            >>>     res = fib(3)

            >>> # Enable time statistics and output summary report
            >>> with Tracer(trace_fn=[fib], time_trace=True):
            >>>     res = fib(3)

            >>> # Persist logs to file
            >>> with Tracer(trace_fn=[fib], logging_path="./trace.log"):
            >>>     res = fib(3)

            >>> # Enter interactive shell before tracing starts
            >>> with Tracer(trace_fn=[fib], interactive=True):
            >>>     res = fib(3)
        """
        target_names = set()
        self.interactive = interactive
        self.interactive_on_event = interactive_on_event
        if trace_fn is not None:
            target_names.update(f.__name__ for f in trace_fn)

        self.target_names = target_names if target_names else None

        filter = set()
        if interactive_filter:
            filter.update(f.__name__ for f in interactive_filter)
        self.filter = filter if filter else None

        logger = Log(logging_path=logging_path).get_logger() if logging_path else None
        self.ctx = TraceContext(logger=logger,
                                time_trace=time_trace,
                                set_color=use_color,
                                exception_trace=exception_trace,
                                show_locals=show_locals,
                                exception_json_path=exception_json_path)
    @property
    def errors(self):
        """TraceErrors collector (None when exception_trace is disabled)."""
        return self.ctx.errors
    @property
    def stats(self):
        return self.ctx.stats
    def hook(self, frame, event, arg):
        return frame_callback(self.ctx,
                              self.target_names,
                              self.interactive_on_event,
                              self.filter,
                              frame, event, arg)
    def __enter__(self):
        if self.interactive:
            namespace = {}
            namespace.update(globals())
            namespace.update(locals())
            SetInteract(namespace=namespace,
                        func_name="",
                        event="call",
                        arg_text="++++++")
        sys.settrace(self.hook)
        return self
    def __exit__(self, *_):
        sys.settrace(None)
        # returns None -> exceptions raised in the block keep propagating
        self.ctx.finish()