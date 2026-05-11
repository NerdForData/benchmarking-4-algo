import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from benchmark.metrics import calculate_makespan


class MWKRScheduler:
    """
    Most Work Remaining (MWKR) Priority Dispatching Rule for Job Shop Scheduling.

    MWKR is the strongest classical dispatching rule for JSP:
      - At each scheduling step, only operations whose predecessor is already scheduled
        are eligible (precedence is always respected).
      - Among eligible operations, the one whose job has the most remaining work
        (sum of durations of all unscheduled operations in that job) is dispatched first.
      - This heuristic prioritises bottleneck jobs and empirically produces much tighter
        makespans than SPT.
    """

    def __init__(self, instance):
        self.instance = instance

    def _get_jobs(self):
        if isinstance(self.instance, dict):
            return self.instance.get("jobs", [])
        return getattr(self.instance, "jobs", [])

    def solve(self):
        jobs = self._get_jobs()

        # Track how many operations each job has completed
        next_op = [0] * len(jobs)                       # index of next unscheduled op per job
        machine_available = [0] * (
            max(machine for job in jobs for machine, _ in job) + 1
        )
        job_available = [0] * len(jobs)

        schedule = []
        total_ops = sum(len(job) for job in jobs)

        for _ in range(total_ops):
            # Build the set of currently eligible operations
            # (the next unscheduled operation of each job that still has ops left)
            eligible = []
            for job_id, job in enumerate(jobs):
                op_idx = next_op[job_id]
                if op_idx < len(job):
                    machine, duration = job[op_idx]
                    # Remaining work = sum of durations of this op + all later ops in the job
                    remaining_work = sum(d for _, d in job[op_idx:])
                    eligible.append((job_id, op_idx, machine, duration, remaining_work))

            if not eligible:
                break

            # MWKR: pick the eligible operation whose job has the most remaining work
            eligible.sort(key=lambda x: -x[4])
            job_id, op_idx, machine, duration, _ = eligible[0]

            # Schedule it at the earliest feasible time
            start = max(machine_available[machine], job_available[job_id])
            end = start + duration

            machine_available[machine] = end
            job_available[job_id] = end
            next_op[job_id] += 1

            schedule.append({
                "job": job_id,
                "operation": op_idx,
                "machine": machine,
                "start": start,
                "end": end,
                "duration": duration
            })

        return {
            "schedule": schedule,
            "makespan": calculate_makespan(schedule),
            "status": "HEURISTIC"
        }


# Keep SPT available as a baseline for reference, but fixed to respect precedence
class SPTScheduler:
    """
    Shortest Processing Time (SPT) dispatching — fixed to respect job precedence.

    The original implementation sorted ALL operations globally by duration and dispatched
    them in that order, which violated JSP constraints (an operation could be dispatched
    before its predecessor in the same job). This version uses the same active-list
    approach as MWKR but uses shortest processing time as the priority criterion.

    Kept here for reference / baseline comparison. MWKR is the recommended default.
    """

    def __init__(self, instance):
        self.instance = instance

    def _get_jobs(self):
        if isinstance(self.instance, dict):
            return self.instance.get("jobs", [])
        return getattr(self.instance, "jobs", [])

    def solve(self):
        jobs = self._get_jobs()

        next_op = [0] * len(jobs)
        machine_available = [0] * (
            max(machine for job in jobs for machine, _ in job) + 1
        )
        job_available = [0] * len(jobs)

        schedule = []
        total_ops = sum(len(job) for job in jobs)

        for _ in range(total_ops):
            eligible = []
            for job_id, job in enumerate(jobs):
                op_idx = next_op[job_id]
                if op_idx < len(job):
                    machine, duration = job[op_idx]
                    eligible.append((job_id, op_idx, machine, duration))

            if not eligible:
                break

            # SPT: pick the eligible operation with the shortest processing time
            eligible.sort(key=lambda x: x[3])
            job_id, op_idx, machine, duration = eligible[0]

            start = max(machine_available[machine], job_available[job_id])
            end = start + duration

            machine_available[machine] = end
            job_available[job_id] = end
            next_op[job_id] += 1

            schedule.append({
                "job": job_id,
                "operation": op_idx,
                "machine": machine,
                "start": start,
                "end": end,
                "duration": duration
            })

        return {
            "schedule": schedule,
            "makespan": calculate_makespan(schedule),
            "status": "HEURISTIC"
        }