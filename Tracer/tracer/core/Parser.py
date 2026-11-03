# Parser.py
from typing import Callable
from .TraceContext import TraceContext
from tracer.interact import SetInteract
from .Color import set_color
def frame_callback(
        ctx: TraceContext,
        target_set: set | None,
        interactive_on_event:bool,
        interactive_filter:set|None,
        frame,
        event,
        arg
) -> Callable | None:
    func_name = frame.f_code.co_name

    if target_set is not None and func_name not in target_set:
        return None
    output_line: str | None = None

    if event == "call":
        if ctx.time_trace and ctx.stats:
            ctx.stats.enter_func(frame, func_name)
        var_names = frame.f_code.co_varnames
        args_str = [f"{name}={repr(frame.f_locals[name])}" for name in var_names]
        arg_text = ", ".join(args_str)
        if ctx.set_color:
            func_str = f"{func_name}({arg_text})"
            func_str = set_color(s=func_str,color="green")
            output_line = f"{ctx.prefix}-> {func_str}"
        else:
            output_line = f"{ctx.prefix}-> {func_name}({arg_text})"
        if interactive_on_event:
            namespace = {}
            namespace.update(globals())
            namespace.update(frame.f_locals)
            SetInteract(namespace=namespace,func_name=func_name,event=event,arg_text=arg_text)
        elif interactive_filter is not None and func_name in interactive_filter:
            namespace = {}
            namespace.update(globals())
            namespace.update(frame.f_locals)
            SetInteract(namespace=namespace,func_name=func_name,event=event,arg_text=arg_text)
        ctx.indent()

    elif event == "exception":
        # arg = (exc_type, exc_value, traceback)
        # Fires once per frame the exception travels through, including frames
        # that are NOT part of target_set (they still show up in the tb chain).
        if ctx.exception_trace and ctx.errors is not None:
            ctx.pending_exc[frame] = ctx.errors.observe(func_name, arg, frame)

    elif event == "line":
        # Execution resumed in this frame => any pending exception was swallowed
        # here (try/except inside the traced function).
        if ctx.pending_exc:
            rec = ctx.pending_exc.pop(frame, None)
            if rec is not None and ctx.errors is not None:
                ctx.errors.mark_handled(rec, func_name)

    elif event == "return":
        pending_rec = ctx.pending_exc.pop(frame, None) if ctx.pending_exc else None
        cost = None
        if ctx.time_trace and ctx.stats:
            _,cost = ctx.stats.exit_func(frame)

        if pending_rec is not None:
            # frame is unwinding because of an exception, not returning a value
            if ctx.set_color:
                func_str = set_color(s=f"{func_name}",color="green")
                exc_str = set_color(s=f"{pending_rec.exc_type}: {pending_rec.message}",color="red")
                output_line = f"{ctx.prefix}<- {func_str} raised {exc_str}"
            else:
                output_line = (f"{ctx.prefix}<- {func_name} raised "
                               f"{pending_rec.exc_type}: {pending_rec.message}")
        else:
            if ctx.set_color:
                if cost is not None:
                    func_str = f"{func_name}"
                    func_str = set_color(s=func_str,color="green")
                    return_str = f"{repr(arg)}"
                    return_str = set_color(s=return_str,color="blue")
                    cost_str = f"{cost:.6f}"
                    cost_str= set_color(s=cost_str,color="yellow")
                    output_line = f"{ctx.prefix}<- {func_str} returned {return_str} | cost={cost_str}s"
                else:
                    func_str = f"{func_name}"
                    func_str = set_color(s=func_str,color="green")
                    return_str = f"{repr(arg)}"
                    return_str = set_color(s=return_str,color="blue")
                    output_line = f"{ctx.prefix}<- {func_str} returned {return_str}"
            else:
                if cost is not None:
                    output_line = f"{ctx.prefix}<- {func_name} returned {repr(arg)} | cost={cost:.6f}s"
                else:
                    output_line = f"{ctx.prefix}<- {func_name} returned {repr(arg)}"

        if interactive_on_event:
            namespace = {}
            namespace.update(globals())
            namespace.update(frame.f_locals)
            SetInteract(namespace=namespace,func_name=func_name,event=event,returned=repr(arg))
        elif interactive_filter is not None and func_name in interactive_filter:
            namespace = {}
            namespace.update(globals())
            namespace.update(frame.f_locals)
            SetInteract(namespace=namespace,
                        func_name=func_name,
                        event=event,
                        returned=repr(arg))
        ctx.dedent()

    if output_line is not None:
        ctx.add(output_line)
    def next_hook(f, e, a):
        return frame_callback(ctx,
                              target_set,
                              interactive_on_event,
                              interactive_filter,
                              f, e, a)
    return next_hook
