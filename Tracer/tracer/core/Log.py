import logging

class Log:
    def __init__(
            self,
            logging_path):
        self.logger = logging.getLogger(f"tracer_{id(logging_path)}")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            file_handler = logging.FileHandler(logging_path, encoding="utf-8", mode="a")
            fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(fmt)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger
