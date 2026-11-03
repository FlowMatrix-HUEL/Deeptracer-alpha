# TraceContext.py
from .TraceStats import TraceStats
from tracer.exceptions.TraceError import TraceErrors

class TraceContext:
    def __init__(self,
                 logger,
                 time_trace:bool=False,
                 set_color:bool=False,
                 exception_trace:bool=False,
                 show_locals:bool=False,
                 exception_json_path:str|None=None):
        self.prefix = ""
        self.logger = logger
        self.time_trace = time_trace
        self.set_color = set_color
        self.output_content = []
        self.stats = TraceStats() if time_trace else None

        self.exception_trace = exception_trace
        self.show_locals = show_locals
        self.exception_json_path = exception_json_path
        self.errors = TraceErrors(show_locals=show_locals) if exception_trace else None
        # frame -> ExcRecord : exception raised in that frame, not yet resolved
        self.pending_exc: dict = {}

    def indent(self):
        self.prefix += "|  "

    def dedent(self):
        if len(self.prefix) >= 3:
            self.prefix = self.prefix[:-3]
    def add(self,output_line):
        self.output_content.append(output_line)    
    def outputcontrol(self):
        for line in self.output_content:
            print(line)
            if self.logger is not None:
                self.logger.info(line)
        self.output_content.clear()

    def finish(self):
        """Flush buffered trace output, then emit exception/time reports."""
        self.outputcontrol()
        if self.exception_trace and self.errors is not None:
            self.errors.finalize()
            self.errors.print_report(setcolor=self.set_color)
            if self.exception_json_path:
                self.errors.export_json(self.exception_json_path)
        if self.time_trace and self.stats is not None:
            self.stats.print_report(setcolor=self.set_color)
