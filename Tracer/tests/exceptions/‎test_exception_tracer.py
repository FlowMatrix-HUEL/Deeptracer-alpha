from tracer import tracer


def add(x, y):
    return x + y


def risky(n):
    # deep_untraced is NOT in trace_fn, but it will still appear in the stack
    return deep_untraced(n)


def deep_untraced(n):
    if n < 0:
        raise ValueError(f"negative depth: {n}")
    return n * 2


def swallowed():
    try:
        raise KeyError("swallowed_key")
    except KeyError:
        return "recovered"


@tracer(trace_fn=[add, risky, swallowed],
        trace_entity=True,
        exception_trace=True,
        show_locals=True)
def run():
    swallowed()
    return add(risky(3), risky(-1))


if __name__ == "__main__":
    try:
        run()
    except ValueError as e:
        print(f"[outside] caught: {type(e).__name__}: {e}")

    print("\n--- programmatic access ---")
    recs = run.tracer_ctx.errors.to_list()
    for r in recs:
        print(r["exc_type"], "|", r["status"], "|", r["propagation_path"])