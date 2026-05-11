import time


def calculate_makespan(schedule):
    """Return the completion time of the last operation across all machines."""
    if not schedule:
        return None
    return max(op["end"] for op in schedule)


class Timer:
    """Context manager that measures wall-clock elapsed time in seconds."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.perf_counter()
        self.elapsed = round(self.end - self.start, 4)