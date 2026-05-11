import os
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from algorithm.dispatching import MWKRScheduler
from algorithm.genetic_algorithm import GeneticAlgorithm
from algorithm.tabu_search import TabuSearch
from algorithm.cp_sat_solver import CPSATScheduler

from benchmark.evaluator import Evaluator
from utils.parser import load_taillard_instance


# ---------------------------------------------------------------------------
# Known best solutions from JSPLIB (tamy0612/JSPLIB instances.json).
# Source: https://github.com/tamy0612/JSPLIB
# These are Best Known Solutions (BKS) / proven optima where available.
# Used to compute optimality_gap_pct = (makespan - bks) / bks * 100.
# ---------------------------------------------------------------------------
KNOWN_OPTIMA = {
    # Fisher & Thompson
    "ft06": 55, "ft10": 930, "ft20": 1165,
    # Adams, Balas & Zawack
    "abz5": 1234, "abz6": 943, "abz7": 656, "abz8": 665, "abz9": 679,
    # Lawrence
    "la01": 666,  "la02": 655,  "la03": 597,  "la04": 590,  "la05": 593,
    "la06": 926,  "la07": 890,  "la08": 863,  "la09": 951,  "la10": 958,
    "la11": 1222, "la12": 1039, "la13": 1150, "la14": 1292, "la15": 1207,
    "la16": 945,  "la17": 784,  "la18": 848,  "la19": 842,  "la20": 902,
    "la21": 1046, "la22": 927,  "la23": 1032, "la24": 935,  "la25": 977,
    "la26": 1218, "la27": 1235, "la28": 1216, "la29": 1152, "la30": 1355,
    "la31": 1784, "la32": 1850, "la33": 1719, "la34": 1721, "la35": 1888,
    "la36": 1268, "la37": 1397, "la38": 1196, "la39": 1233, "la40": 1222,
    # Applegate & Cook
    "orb01": 1059, "orb02": 888, "orb03": 1005, "orb04": 1005, "orb05": 887,
    "orb06": 1010, "orb07": 397, "orb08": 899,  "orb09": 934,  "orb10": 944,
    # Storer, Wu & Vaccari (BKS, not all proven optimal)
    "swv01": 1407, "swv02": 1475, "swv03": 1398, "swv04": 1470, "swv05": 1424,
    "swv06": 1671, "swv07": 1594, "swv08": 1751, "swv09": 1655, "swv10": 1743,
    "swv11": 2983, "swv12": 2972, "swv13": 3104, "swv14": 2968, "swv15": 2885,
    "swv16": 2924, "swv17": 2794, "swv18": 2852, "swv19": 2843, "swv20": 2823,
    # Yamada & Nakano
    "yn1": 884, "yn2": 904, "yn3": 892, "yn4": 968,
    # Taillard (BKS)
    "ta01": 1231, "ta02": 1244, "ta03": 1218, "ta04": 1175, "ta05": 1224,
    "ta06": 1238, "ta07": 1227, "ta08": 1217, "ta09": 1274, "ta10": 1241,
    "ta11": 1357, "ta12": 1367, "ta13": 1342, "ta14": 1345, "ta15": 1339,
    "ta16": 1360, "ta17": 1462, "ta18": 1396, "ta19": 1332, "ta20": 1348,
    "ta21": 1642, "ta22": 1600, "ta23": 1557, "ta24": 1647, "ta25": 1595,
    "ta26": 1643, "ta27": 1680, "ta28": 1603, "ta29": 1625, "ta30": 1584,
    "ta31": 1764, "ta32": 1796, "ta33": 1831, "ta34": 1829, "ta35": 2007,
    "ta36": 1819, "ta37": 1771, "ta38": 1673, "ta39": 1795, "ta40": 1631,
    "ta41": 2005, "ta42": 1937, "ta43": 1846, "ta44": 1979, "ta45": 2000,
    "ta46": 2011, "ta47": 1903, "ta48": 1952, "ta49": 1968, "ta50": 1926,
    "ta51": 2760, "ta52": 2756, "ta53": 2717, "ta54": 2839, "ta55": 2679,
    "ta56": 2781, "ta57": 2943, "ta58": 2885, "ta59": 2655, "ta60": 2723,
    "ta61": 3045, "ta62": 2869, "ta63": 3003, "ta64": 2755, "ta65": 2725,
    "ta66": 2845, "ta67": 2825, "ta68": 2784, "ta69": 3071, "ta70": 2995,
    "ta71": 5464, "ta72": 5181, "ta73": 5568, "ta74": 5339, "ta75": 5392,
    "ta76": 5342, "ta77": 5436, "ta78": 5394, "ta79": 5358, "ta80": 5183,
}


class BenchmarkRunner:
    """
    Runs all four algorithms on every instance file in data_folder and writes
    a CSV to results/benchmark_results.csv.

    CSV columns (industry standard for JSP benchmarks):
      instance          - filename (e.g. ta01, la16)
      num_jobs          - number of jobs in the instance
      num_machines      - number of machines in the instance
      algorithm         - algorithm name
      makespan          - makespan achieved
      bks               - best known solution from JSPLIB (None if unknown)
      optimality_gap_pct- (makespan - bks) / bks * 100  (None if bks unknown)
      runtime_s         - wall-clock seconds (4 d.p.)
      status            - OPTIMAL / FEASIBLE / HEURISTIC / NO_SOLUTION
    """

    def __init__(self, data_folder="data/taillard_dataset/instances"):
        self.data_folder = Path(data_folder)

    def _get_bks(self, filename):
        """Look up the best known solution for an instance by filename stem."""
        key = Path(filename).stem.lower()
        return KNOWN_OPTIMA.get(key, None)

    def run(self):
        results = []

        files = sorted(f for f in self.data_folder.glob("*") if f.is_file())

        for file in files:
            print(f"\nRunning benchmark on: {file.name}")

            instance = load_taillard_instance(file)
            num_jobs = instance["num_jobs"]
            num_machines = instance["num_machines"]
            bks = self._get_bks(file.name)

            algorithms = {
                "MWKR":   MWKRScheduler(instance),
                "GA":     GeneticAlgorithm(instance),
                "Tabu":   TabuSearch(instance),
                "CP-SAT": CPSATScheduler(instance),
            }

            for name, algorithm in algorithms.items():
                print(f"  Running {name}...", end=" ", flush=True)

                evaluator = Evaluator(name, algorithm)
                result = evaluator.evaluate()

                makespan = result["makespan"]
                if makespan is not None and bks is not None:
                    gap = round((makespan - bks) / bks * 100, 2)
                else:
                    gap = None

                results.append({
                    "instance":            file.name,
                    "num_jobs":            num_jobs,
                    "num_machines":        num_machines,
                    "algorithm":           result["algorithm"],
                    "makespan":            makespan,
                    "bks":                 bks,
                    "optimality_gap_pct":  gap,
                    "runtime_s":           result["runtime"],
                    "status":              result["status"],
                })

                print(f"makespan={makespan}  gap={gap}%  [{result['status']}]  {result['runtime']}s")

        df = pd.DataFrame(results)

        # Column order for readability
        df = df[[
            "instance", "num_jobs", "num_machines",
            "algorithm", "makespan", "bks", "optimality_gap_pct",
            "runtime_s", "status"
        ]]

        Path("results").mkdir(exist_ok=True)
        out_path = "results/benchmark_results.csv"
        df.to_csv(out_path, index=False)

        print(f"\nBenchmark completed. Results saved to {out_path}")
        print(df.to_string(index=False))

        return df