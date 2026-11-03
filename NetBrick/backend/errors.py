class ShapeError(ValueError):
    def __init__(self, message: str, tip: str = "") -> None:
        super().__init__(message)
        self.tip = tip
