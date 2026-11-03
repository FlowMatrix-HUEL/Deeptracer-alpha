import timeit
from typing import Callable,Optional,Tuple,List,Dict
import json
import time

def time_tracer(
    target: Callable,
    args:Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    number: int = 1000,
    repeat: int = 5,
    save_json_path: Optional[str] = None,
    use_process_time: bool = False
):
    """
    Benchmark function based on timeit, support passing positional & keyword arguments.
    Pure standard library only, export full structured data to JSON file optionally.

    Args:
        target: Target function to benchmark
        args: Tuple of positional arguments passed to target, e.g. (3, 5)
        kwargs: Dict of keyword arguments passed to target, e.g. {"c": 10}
        number: Execute target N times per measurement round
        repeat: Total measurement rounds
        save_json_path: Path to dump benchmark JSON report, skip file write if None
        use_process_time: Use process CPU time instead of wall-clock perf counter

    Returns:
        Structured benchmark data dict
    """
    args = args or ()
    kwargs = kwargs or {}
    clock = time.process_time if use_process_time else time.perf_counter
    if args or kwargs:
        timer = timeit.Timer(stmt=lambda:target(*args,**kwargs),timer=clock)
    else:
        timer = timeit.Timer(stmt=target,timer=clock)

    raw_round_times: List[float] = timer.repeat(repeat=repeat, number=number)

    total_runs = repeat * number
    min_round = min(raw_round_times)
    max_round = max(raw_round_times)
    avg_round = sum(raw_round_times) / len(raw_round_times)

    report = {
        "meta": {
            "timestamp": time.time(),
            "func_name": target.__name__,
            "args": args,
            "kwargs": kwargs,
            "repeat_rounds": repeat,
            "exec_per_round": number,
            "total_executions": total_runs,
            "use_process_time": use_process_time
        },
        "raw_round_seconds": raw_round_times,
        "aggregated": {
            "round_min_s": min_round,
            "round_avg_s": avg_round,
            "round_max_s": max_round,
            "single_call_min_s": min_round / number,
            "single_call_avg_s": avg_round / number,
            "single_call_max_s": max_round / number
        }
    }

    if save_json_path is not None:
        try:
            with open(save_json_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise IOError(f"Failed to write benchmark JSON to {save_json_path}: {str(e)}") from e
    return report