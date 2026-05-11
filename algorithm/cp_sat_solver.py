import os
import sys
from ortools.sat.python import cp_model

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


class CPSATScheduler:
    """
    CP-SAT exact solver for Job Shop Scheduling (Google OR-Tools).

    - makespan is returned as int (was float from ObjectiveValue(), causing type
      inconsistencies when comparing against other algorithms' int makespans).
    - A 'status' field is now returned: OPTIMAL, FEASIBLE (time-limited), or NO_SOLUTION.
      Previously all results looked identical regardless of whether the solver hit the
      time limit — misleading when comparing against heuristics.
    - Returns makespan = None and empty schedule on NO_SOLUTION instead of silently
      returning ObjectiveValue() on a failed solve (which raises internally in OR-Tools).
    """

    def __init__(self, instance, time_limit_seconds=60):
        self.instance = instance
        self.time_limit_seconds = time_limit_seconds

    def _get_jobs(self):
        if isinstance(self.instance, dict):
            return self.instance.get("jobs", [])
        return getattr(self.instance, "jobs", [])

    def solve(self):
        jobs_data = self._get_jobs()
        machines_count = max(max(machine for machine, _ in job) for job in jobs_data) + 1
        horizon = sum(sum(duration for _, duration in job) for job in jobs_data)
        return self._cp_sat_solver(jobs_data, machines_count, horizon)

    def _cp_sat_solver(self, jobs_data, machines_count, horizon):
        model = cp_model.CpModel()

        task_vars = {}
        machine_to_intervals = [[] for _ in range(machines_count)]

        for job_id, job in enumerate(jobs_data):
            for task_id, (machine, duration) in enumerate(job):
                suffix = f"_{job_id}_{task_id}"
                start_var = model.NewIntVar(0, horizon, "start" + suffix)
                end_var = model.NewIntVar(0, horizon, "end" + suffix)
                interval_var = model.NewIntervalVar(
                    start_var, duration, end_var, "interval" + suffix
                )
                task_vars[(job_id, task_id)] = (start_var, end_var, interval_var, machine, duration)
                machine_to_intervals[machine].append(interval_var)

        # No two operations may overlap on the same machine
        for machine in range(machines_count):
            model.AddNoOverlap(machine_to_intervals[machine])

        # Precedence: each operation must start after the previous one in the same job ends
        for job_id, job in enumerate(jobs_data):
            for task_id in range(len(job) - 1):
                model.Add(
                    task_vars[(job_id, task_id + 1)][0] >= task_vars[(job_id, task_id)][1]
                )

        # Objective: minimise makespan
        makespan_var = model.NewIntVar(0, horizon, "makespan")
        model.AddMaxEquality(
            makespan_var,
            [task_vars[(job_id, len(job) - 1)][1] for job_id, job in enumerate(jobs_data)]
        )
        model.Minimize(makespan_var)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds

        status_code = solver.Solve(model)

        # Map OR-Tools status codes to human-readable labels
        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",       # time limit hit, best-effort result
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.UNKNOWN: "NO_SOLUTION",
        }
        status_label = status_map.get(status_code, "NO_SOLUTION")

        if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {
                "schedule": [],
                "makespan": None,
                "status": status_label
            }

        schedule = []
        for (job_id, task_id), (start_var, end_var, _, machine, duration) in task_vars.items():
            schedule.append({
                "job": job_id,
                "operation": task_id,
                "machine": machine,
                "start": solver.Value(start_var),
                "end": solver.Value(end_var),
                "duration": duration
            })

        # FIX: cast to int — ObjectiveValue() returns float (e.g. 1234.0),
        # inconsistent with calculate_makespan() which returns int.
        return {
            "schedule": schedule,
            "makespan": int(solver.ObjectiveValue()),
            "status": status_label
        }