from dataclasses import dataclass
import time
from .Color import set_color

@dataclass
class FuncStat:
    call_count: int = 0
    total_cost: float = 0.0
    min_cost: float = float("inf")
    max_cost: float = 0.0

    def add_record(self,
                   cost: float):
        self.call_count += 1
        self.total_cost += cost
        if cost < self.min_cost:
            self.min_cost = cost
        if cost > self.max_cost:
            self.max_cost = cost

    @property
    def avg_cost(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.total_cost / self.call_count
    
class TraceStats:
    def __init__(self):
        self.data: dict[str, FuncStat] = {}
        self.running_start: dict[object, tuple[str, float]] = {}

    def enter_func(self, frame, func_name: str):
        start = time.perf_counter()
        self.running_start[frame] = (func_name, start)

    def exit_func(self, frame) -> tuple[str, float] | None:
        if frame not in self.running_start:
            return None
        func_name, start = self.running_start.pop(frame)
        cost = time.perf_counter() - start

        if func_name not in self.data:
            self.data[func_name] = FuncStat()
        self.data[func_name].add_record(cost)
        return func_name, cost

    def print_report(self,
                     setcolor:bool=False):
        if setcolor:
            print("\n===== Function Trace Statistics Report =====")
            function_str = f"{'Function':<16}"
            function_str = set_color(s=function_str,color="blue")
            call_str = f"{'Calls':<8}"
            call_str = set_color(s=call_str,color="blue")
            total_str = f"{'Total(s)':<10}"
            total_str = set_color(s=total_str,color="blue")
            avg_str = f"{'Avg(s)':<10}"
            avg_str = set_color(s=avg_str,color="blue")
            mins_str = f"{'Min(s)':<10}"
            mins_str = set_color(s=mins_str,color='blue')
            maxs_str = f"{'Max(s)':<10}"
            maxs_str = set_color(s=maxs_str,color="blue")
            print(f"{function_str}{call_str}{total_str}{avg_str}{mins_str}{maxs_str}")
            for name, stat in self.data.items():
                name_str = f"{name:<16}"
                name_str = set_color(s=name_str,color='green')
                call_count = f"{stat.call_count:<8}"
                call_count = set_color(s=call_count,color="yellow")
                total_cost = f"{stat.total_cost:<10.4f}"
                total_cost = set_color(s=total_cost,color="yellow")
                avg_cost = f"{stat.avg_cost:<10.4f}"
                avg_cost = set_color(s=avg_cost,color="yellow")
                min_cost = f"{stat.min_cost:<10.4f}"
                min_cost = set_color(s=min_cost,color="yellow")
                max_cost = f"{stat.max_cost:<10.4f}"
                max_cost = set_color(s=max_cost,color="yellow")
                print(f"{name_str}{call_count}{total_cost}{avg_cost}{min_cost}{max_cost}")
            print("============================================\n")
        else:
            print("\n===== Function Trace Statistics Report =====")
            print(f"{'Function':<16}{'Calls':<8}{'Total(s)':<10}{'Avg(s)':<10}{'Min(s)':<10}{'Max(s)':<10}")
            for name, stat in self.data.items():
                print(f"{name:<16}{stat.call_count:<8}{stat.total_cost:<10.4f}{stat.avg_cost:<10.4f}{stat.min_cost:<10.4f}{stat.max_cost:<10.4f}")
            print("============================================\n")