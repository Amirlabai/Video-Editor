"""
Progress reporting protocol for headless and GUI consumers.
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class ProgressReporter(Protocol):
    def on_progress(self, metrics: dict) -> None: ...
    def on_log(self, line: str) -> None: ...
    def on_file_status(self, index: int, status: str) -> None: ...


class NullProgressReporter:
    """No-op reporter."""

    def on_progress(self, metrics: dict) -> None:
        pass

    def on_log(self, line: str) -> None:
        pass

    def on_file_status(self, index: int, status: str) -> None:
        pass


class PrintProgressReporter:
    """CLI-friendly reporter that prints logs and periodic progress."""

    def __init__(self):
        self._last_percent = -1

    def on_progress(self, metrics: dict) -> None:
        percent = metrics.get("percent", 0)
        if int(percent) % 5 == 0 and int(percent) != self._last_percent:
            self._last_percent = int(percent)
            fps = metrics.get("fps", 0)
            remaining = metrics.get("time_remaining", "")
            print(f"Progress: {percent:.2f}% | FPS: {fps:.1f} | Rem: {remaining}")

    def on_log(self, line: str) -> None:
        print(line, end="" if line.endswith("\n") else "\n")

    def on_file_status(self, index: int, status: str) -> None:
        print(f"File {index}: {status}")


def get_reporter(reporter: Optional[ProgressReporter]) -> ProgressReporter:
    return reporter if reporter is not None else NullProgressReporter()
