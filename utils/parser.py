from pathlib import Path


def load_taillard_instance(file_path):
    """
    Load a JSP instance file.

    Supports two formats found in JSPLIB:

    1. Standard OR-Library format (used by abz, ft, la, orb, swv, yn):
       Line 0: <num_jobs> <num_machines>
       Lines 1..num_jobs: pairs of <machine> <duration> interleaved on one line
       e.g.  0 29  1 78  2 9  3 36  4 49  5 11  ...

    2. Taillard format (used by ta* instances):
       Line 0: <num_jobs> <num_machines>
       Next num_jobs lines: machine indices (one per operation)
       Next num_jobs lines: processing times (one per operation)
       The two halves are matched column-by-column.

    The function auto-detects which format is used based on whether the
    total number of data lines after the header equals num_jobs (Taillard)
    or 2*num_jobs (Taillard split) or the values per line are pairs (OR-Library).
    """
    file_path = Path(file_path)

    with open(file_path, "r") as f:
        lines = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    num_jobs, num_machines = map(int, lines[0].split())
    data_lines = lines[1:]

    jobs = []

    # Detect format: Taillard format has 2*num_jobs data lines (machines then times),
    # OR-Library format has num_jobs lines each with 2*num_machines values.
    if len(data_lines) == 2 * num_jobs:
        # Taillard format: first block = machine order, second block = durations
        machine_block = data_lines[:num_jobs]
        time_block = data_lines[num_jobs:]

        for m_line, t_line in zip(machine_block, time_block):
            machines = list(map(int, m_line.split()))
            times = list(map(int, t_line.split()))
            operations = list(zip(machines, times))
            jobs.append(operations)

    else:
        # OR-Library format: each line has interleaved <machine> <duration> pairs
        for line in data_lines[:num_jobs]:
            values = list(map(int, line.split()))
            operations = []
            for i in range(0, len(values), 2):
                machine = values[i]
                processing_time = values[i + 1]
                operations.append((machine, processing_time))
            jobs.append(operations)

    return {
        "num_jobs": num_jobs,
        "num_machines": num_machines,
        "jobs": jobs
    }