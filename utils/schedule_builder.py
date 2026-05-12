from collections import defaultdict


class ScheduleBuilder:
    """
    Builds a feasible JSP schedule by dispatching operations one at a time.

    GA and Tabu represent solutions as shuffled permutations of all operations.
    When they call add_operation(), op k+1 of a job often arrives before op k.

    Without the queue, the old builder placed op k+1 immediately using
    job_available[job_id] = 0 (since op k hadn't run yet), scheduling it at
    time 0 in violation of JSP precedence. This produced makespans shorter
    than the known optimum — negative optimality gaps — which are impossible
    for a valid schedule.

    Operations that arrive out of order are held in self._pending.
    After every placement, _flush_pending() replays the queue and places
    any operation whose predecessor has now completed. This guarantees
    strict operation ordering within every job, regardless of the order
    the caller passes operations in.

    MWKR and CP-SAT always pass operations in valid order and are unaffected.
    """

    def __init__(self, instance):
        self.instance = instance
        self.machine_available = defaultdict(int)
        self.job_available = defaultdict(int)
        self.next_op = defaultdict(int)   # next expected operation index per job
        self._pending = []                # out-of-order operations waiting to be placed
        self.schedule = []

    def add_operation(self, job_id, operation_id, machine, duration):
        """
        Schedule an operation. If its predecessor in the same job has not yet
        been placed, queue it and wait — _flush_pending() will place it once
        the predecessor is done.
        """
        if operation_id != self.next_op[job_id]:
            self._pending.append((job_id, operation_id, machine, duration))
        else:
            self._place(job_id, operation_id, machine, duration)
            self._flush_pending()

    def _place(self, job_id, operation_id, machine, duration):
        """Place one operation at the earliest feasible time."""
        start_time = max(
            self.machine_available[machine],
            self.job_available[job_id]
        )
        end_time = start_time + duration

        self.machine_available[machine] = end_time
        self.job_available[job_id] = end_time
        self.next_op[job_id] += 1

        self.schedule.append({
            "job": job_id,
            "operation": operation_id,
            "machine": machine,
            "start": start_time,
            "end": end_time,
            "duration": duration
        })

    def _flush_pending(self):
        """
        Drain the pending queue. Keep scanning until no more operations
        can be placed (i.e. no progress in a full pass).
        """
        progress = True
        while progress:
            progress = False
            remaining = []
            for op in self._pending:
                job_id, operation_id, machine, duration = op
                if operation_id == self.next_op[job_id]:
                    self._place(job_id, operation_id, machine, duration)
                    progress = True
                else:
                    remaining.append(op)
            self._pending = remaining

    def get_schedule(self):
        return self.schedule