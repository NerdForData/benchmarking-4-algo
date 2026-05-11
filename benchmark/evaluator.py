import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from benchmark.metrics import Timer


class Evaluator:
    """
    Wraps any algorithm and measures its wall-clock runtime.
    - It passes the 'status' field from the algorithm result through to the caller.
      This is essential for CP-SAT, which distinguishes OPTIMAL vs FEASIBLE (time-limited)
      vs NO_SOLUTION. Without it, all CP-SAT results looked identical in the CSV regardless
      of whether the solver found a proven optimum or hit the 60-second time limit.
    - Heuristic algorithms (GA, Tabu, MWKR) return status="HEURISTIC" by convention.
    """

    def __init__(self, algorithm_name, algorithm):
        self.algorithm_name = algorithm_name
        self.algorithm = algorithm

    def evaluate(self):
        with Timer() as timer:
            result = self.algorithm.solve()

        return {
            "algorithm": self.algorithm_name,
            "makespan": result["makespan"],
            "runtime": timer.elapsed,
            "status": result.get("status", "UNKNOWN"),
            "schedule": result["schedule"]
        }