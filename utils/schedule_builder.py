from collections import defaultdict


class ScheduleBuilder:
    """
    Builds a JSP schedule by dispatching operations one at a time.

    For each operation, the start time is:
        max(machine_available[machine], job_available[job_id])

    This means:
    - A machine cannot start a new operation before it finishes the current one.
    - A job's next operation cannot start before its previous operation finishes.

    Note: ScheduleBuilder enforces feasibility regardless of the order in which
    operations are added. Algorithms (GA, Tabu) rely on this to handle chromosomes
    whose gene order does not match job-operation order — the builder silently
    defers an operation until both its machine and job predecessor are free.

    This is correct behaviour for permutation-based metaheuristics but means the
    builder alone does NOT guarantee that the chromosome order matches the actual
    dispatching order. Always reconstruct the schedule from the builder output,
    not from the chromosome directly.
    """

    def __init__(self, instance):
        self.instance = instance
        self.machine_available = defaultdict(int)
        self.job_available = defaultdict(int)
        self.schedule = []

    def add_operation(self, job_id, operation_id, machine, duration):
        start_time = max(
            self.machine_available[machine],
            self.job_available[job_id]
        )
        end_time = start_time + duration

        self.machine_available[machine] = end_time
        self.job_available[job_id] = end_time

        self.schedule.append({
            "job": job_id,
            "operation": operation_id,
            "machine": machine,
            "start": start_time,
            "end": end_time,
            "duration": duration
        })

    def get_schedule(self):
        return self.schedule