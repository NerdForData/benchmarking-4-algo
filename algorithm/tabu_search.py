import os
import sys
import random
from collections import deque
from copy import deepcopy

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.schedule_builder import ScheduleBuilder
from benchmark.metrics import calculate_makespan


class TabuSearch:
    """
    Tabu Search for Job Shop Scheduling.

    - Tabu list is a set of hashable solution keys → O(1) lookup instead of O(n*m)
    - A deque enforces the tenure window without repeated list.pop(0) (which was O(n))
    - Neighbors are evaluated once and results cached before the admissibility check,
      eliminating the double self.evaluate() call per candidate in the original
    - Aspiration criterion: a tabu move is accepted if it beats the global best
    """

    def __init__(self, instance, iterations=200, tabu_tenure=15):
        self.instance = instance
        self.iterations = iterations
        self.tabu_tenure = tabu_tenure

    def _get_jobs(self):
        if isinstance(self.instance, dict):
            return self.instance.get("jobs", [])
        return getattr(self.instance, "jobs", [])

    def _solution_key(self, solution):
        """
        Convert a solution (list of 4-tuples) to a hashable key.
        We use only (job_id, operation_id) pairs since machine/duration are fixed per op.
        """
        return tuple((g[0], g[1]) for g in solution)

    def create_initial_solution(self):
        operations = []
        for job_id, job in enumerate(self._get_jobs()):
            for operation_id, (machine, duration) in enumerate(job):
                operations.append((job_id, operation_id, machine, duration))
        random.shuffle(operations)
        return operations

    def build_schedule(self, solution):
        builder = ScheduleBuilder(self.instance)
        for job_id, operation_id, machine, duration in solution:
            builder.add_operation(job_id, operation_id, machine, duration)
        return builder.get_schedule()

    def evaluate(self, solution):
        return calculate_makespan(self.build_schedule(solution))

    def generate_neighbors(self, solution, n_neighbors=20):
        """
        Generate candidate neighbors by swapping pairs of operations.
        Returns list of (neighbor, swap_key) tuples.
        """
        neighbors = []
        for _ in range(n_neighbors):
            neighbor = deepcopy(solution)
            i, j = random.sample(range(len(solution)), 2)
            neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
            # The tabu attribute is the pair of operation keys that were swapped
            swap_key = frozenset({(neighbor[i][0], neighbor[i][1]),
                                   (neighbor[j][0], neighbor[j][1])})
            neighbors.append((neighbor, swap_key))
        return neighbors

    def solve(self):
        current_solution = self.create_initial_solution()
        best_solution = deepcopy(current_solution)
        best_cost = self.evaluate(best_solution)

        # Tabu structure: set for O(1) lookup, deque for O(1) eviction
        tabu_set = set()
        tabu_queue = deque()

        for _ in range(self.iterations):
            neighbors = self.generate_neighbors(current_solution)

            # Evaluate all neighbors once, sort by cost
            evaluated = [(self.evaluate(nb), nb, key) for nb, key in neighbors]
            evaluated.sort(key=lambda x: x[0])

            selected = None
            selected_cost = None

            for cost, neighbor, swap_key in evaluated:
                is_tabu = swap_key in tabu_set

                # Aspiration criterion: accept tabu move if it beats the global best
                if not is_tabu or cost < best_cost:
                    selected = neighbor
                    selected_cost = cost
                    selected_key = swap_key
                    break

            if selected is None:
                # All moves are tabu and none beats best — pick least-bad anyway
                selected_cost, selected, selected_key = evaluated[0]

            current_solution = selected

            if selected_cost < best_cost:
                best_solution = deepcopy(selected)
                best_cost = selected_cost

            # Add move to tabu
            tabu_set.add(selected_key)
            tabu_queue.append(selected_key)

            # Evict oldest move when tenure exceeded
            if len(tabu_queue) > self.tabu_tenure:
                evicted = tabu_queue.popleft()
                tabu_set.discard(evicted)

        schedule = self.build_schedule(best_solution)
        return {
            "schedule": schedule,
            "makespan": calculate_makespan(schedule),
            "status": "HEURISTIC"
        }