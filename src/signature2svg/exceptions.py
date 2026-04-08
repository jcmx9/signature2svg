"""Custom exceptions for the vectorization pipeline."""


class NoPathsDetectedError(ValueError):
    """No paths found after vectorization."""

    def __init__(self) -> None:
        super().__init__("No paths detected — check threshold settings")


class PotraceError(RuntimeError):
    """Potrace subprocess failed."""

    def __init__(self, stderr: str) -> None:
        super().__init__(f"Potrace failed: {stderr}")
