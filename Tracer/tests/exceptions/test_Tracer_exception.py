"""Context-manager flavour: recursion propagation + JSON export + programmatic access."""

import json

from tracer import Tracer


def dive(n):
    if n == 0:
        raise RuntimeError("bottom reached")
    return dive(n - 1)


def safe():
    try:
        dive(1)
    except RuntimeError:
        return "handled at safe()"


if __name__ == "__main__":
    json_path = "./tracer_exceptions.json"

    with Tracer(trace_fn=[dive, safe],
                exception_trace=True,
                exception_json_path=json_path) as t:
        try:
            dive(3)      # escapes the traced scope
        except RuntimeError:
            print("[outside] caught the escape")
        safe()           # swallowed by a traced function

    print("--- records ---")
    for r in t.errors.to_list():
        print(f'{r["seq"]}. {r["exc_type"]} :: {r["status"]} :: path={r["propagation_path"]}')

    with open(json_path, encoding="utf-8") as f:
        payload = json.load(f)
    print("--- json summary ---")
    print(payload["summary"])