# JSSP Benchmark  Job Shop Scheduling Problem

A systematic benchmark of four scheduling algorithms against the **JSPLIB / Taillard dataset**, covering 162 standard instances across 7 instance families. The goal is to quantify the quality–speed trade-off between exact, metaheuristic, and dispatching-rule approaches to the Job Shop Scheduling Problem (JSSP).

---

## What is the Job Shop Scheduling Problem?

The Job Shop Scheduling Problem (JSSP) is one of the most studied combinatorial optimisation problems in operations research. Given:

- **n jobs**, each consisting of an ordered sequence of operations
- **m machines**, each capable of processing one operation at a time
- Each operation must be processed on a specific machine for a fixed duration
- Operations within a job must be processed in order (precedence constraint)
- No machine can process two operations simultaneously (capacity constraint)

The objective is to find a schedule that minimises the **makespan**  the total time from start to completion of all jobs.

JSSP is NP-hard for n ≥ 3 jobs and m ≥ 3 machines, meaning no known polynomial-time algorithm can solve all instances optimally. This makes it an ideal benchmark for comparing exact solvers against heuristic approaches.

---

## Project Structure

```
jssp_benchmark/
│
├── main.py                          # Entry point  runs the full benchmark
│
├── algorithm/
│   ├── dispatching.py               # MWKR dispatching rule
│   ├── genetic_algorithm.py         # Genetic Algorithm
│   ├── tabu_search.py               # Tabu Search
│   └── cp_sat_solver.py             # CP-SAT exact solver (OR-Tools)
│
├── benchmark/
│   ├── runner.py                    # Orchestrates all algorithms across all instances
│   ├── evaluator.py                 # Wraps algorithms, measures runtime
│   └── metrics.py                   # makespan calculation, Timer
│
├── utils/
│   ├── parser.py                    # Loads Taillard / OR-Library instance files
│   ├── schedule_builder.py          # Builds feasible schedules from operation sequences
│   └── gantt.py                     # Gantt chart renderer
│
├── data/
│   └── taillard_dataset/
│       └── instances/               # 162 JSPLIB instance files
│
├── results/
│   ├── benchmark_results.csv        # Output  full benchmark results
│   └── plots/                       # Output  generated visualisations
│
└── visualize_benchmark.py           # Generates all 6 plots from the CSV
```

---

## The Four Algorithms

The four algorithms were selected to cover the full spectrum of approaches to JSSP, from the fastest possible dispatching rule to exact constraint programming, allowing a rigorous analysis of the quality–speed trade-off at each tier.

---

### 1. MWKR  Most Work Remaining (Dispatching Rule)

**Category:** Priority dispatching rule  
**Time complexity:** O(n · m) per schedule  
**Why chosen:**

MWKR is the strongest classical priority dispatching rule for JSSP, identified as such by Panwalkar & Iskander (1977) in their landmark survey of 113 scheduling rules. It represents the simplest possible approach to JSSP  no search, no iteration, one pass through all operations.

At each step, only *eligible* operations (those whose predecessor in the same job has already been scheduled) are considered. Among eligible operations, the one whose job has the most remaining work is dispatched first. This prioritises bottleneck jobs and prevents long jobs from being starved at the end of a schedule.

MWKR is included as the **baseline**  the answer to "what is the cost of using no optimisation at all?" It is the only algorithm capable of scheduling in real time (sub-millisecond), making it the natural choice when a schedule must be produced instantly in a production environment, regardless of quality.

It replaced the original SPT (Shortest Processing Time) rule, which was not only weaker in practice but had a code-level precedence violation  it sorted all operations globally by duration, ignoring job ordering constraints entirely.

**Result on this benchmark:** avg gap 57.57%, avg runtime 0.02s, 0 instance wins.

---

### 2. GA  Genetic Algorithm

**Category:** Evolutionary metaheuristic  
**Time complexity:** O(population × generations × n · m)  
**Why chosen:**

Genetic Algorithms are one of the most widely studied metaheuristics for JSSP, with a long publication history dating to Nakano & Yamada (1991) and Davis (1985). They are included because they represent a fundamentally different search strategy from Tabu Search  population-based, global search with crossover recombination  which allows escape from local optima that greedy neighbourhood search cannot.

The GA maintains a population of candidate solutions (chromosomes), each representing a permutation of all operations. In each generation it applies tournament selection, order crossover (OX1), and swap mutation to evolve better solutions, with elitism ensuring the global best is never lost.

GA is included to answer the question: *does population-based global search outperform trajectory-based local search (Tabu) on JSSP?* The benchmark answer is no  Tabu consistently outperforms GA on this problem class  which is itself a meaningful and publishable finding, consistent with the broader JSP literature where Tabu Search dominates evolutionary approaches.

**Result on this benchmark:** avg gap 20.95%, avg runtime 3.90s, 14 instance wins.

---

### 3. Tabu Search

**Category:** Trajectory-based metaheuristic  
**Time complexity:** O(iterations × neighbours × n · m)  
**Why chosen:**

Tabu Search is the most successful metaheuristic for JSSP in the literature. The seminal work of Nowicki & Smutnicki (1996)  the i-TSAB algorithm  held the record for best published results on Taillard instances for over a decade. Dell'Amico & Trubian (1993) and Balas & Vazacopoulos (1998) further established Tabu Search as the method of choice for practical JSSP solving.

It is included because it represents the state of the art among heuristics for this problem: a single solution is iteratively improved by moving to the best neighbouring solution that is not on the *tabu list* (a short-term memory that prevents cycling). An aspiration criterion overrides the tabu restriction when a move leads to a new global best.

Compared to GA, Tabu Search exploits the problem structure more directly  neighbourhood moves correspond to swapping two operations in the dispatching sequence, which is a meaningful local change in schedule space.

**Result on this benchmark:** avg gap 3.63%, avg runtime 2.90s, 64 instance wins  the best heuristic by a wide margin.

---

### 4. CP-SAT  Constraint Programming with SAT (OR-Tools)

**Category:** Exact solver  
**Time complexity:** Exponential worst-case; practical performance depends on instance structure  
**Why chosen:**

CP-SAT (Google OR-Tools) is the current state-of-the-art exact solver for combinatorial scheduling problems. It combines constraint programming, SAT solving, LP relaxations, and large neighbourhood search within a branch-and-bound framework. It has won multiple MiniZinc and scheduling competitions and is the de-facto standard exact solver for JSSP in both industry and academia.

It is included to provide the **gold standard**  the proven optimum against which all heuristics are evaluated. Without an exact solver, the `optimality_gap_pct` column would not exist and the benchmark would have no absolute quality reference. Every gap percentage in the results CSV is computed as `(heuristic_makespan − BKS) / BKS × 100`, where BKS values come from either CP-SAT's OPTIMAL solutions or published literature.

CP-SAT's practical limitation is runtime: it solves small instances (ft, la, abz, orb) to proven optimality in seconds, but hits the 60-second time limit on 90 of the 162 instances (all large ta*, swv*, yn* instances), returning a best-effort FEASIBLE solution rather than a proven optimum.

**Result on this benchmark:** avg gap 1.73%, avg runtime 36.23s, 84 instance wins  best quality, highest cost.

---

## Dataset  JSPLIB / Taillard

All instances are drawn from [JSPLIB](https://github.com/tamy0612/JSPLIB), the standard repository for JSP benchmark instances.

| Family | Source | Instances | Jobs | Machines | Notes |
|--------|--------|-----------|------|----------|-------|
| `ft` | Fisher & Thompson (1963) | 3 | 6–20 | 6–20 | The original JSP benchmark instances; ft06 and ft10 are proven optimal |
| `abz` | Adams, Balas & Zawack (1988) | 5 | 10–20 | 10–15 | Classic medium-size instances |
| `la` | Lawrence (1984) | 40 | 10–15 | 5–15 | Large family; widely used for algorithm comparison |
| `orb` | Applegate & Cook (1991) | 10 | 10 | 10 | All proven optimal |
| `swv` | Storer, Wu & Vaccari (1992) | 20 | 20–50 | 10–15 | Hard instances; many BKS not proven optimal |
| `yn` | Yamada & Nakano (1992) | 4 | 20 | 20 | Dense, hard instances |
| `ta` | Taillard (1993) | 80 | 15–100 | 15–20 | The most widely used benchmark family; ta71–ta80 (100×20) are the hardest |

**Total: 162 instances** spanning problem sizes from 6 jobs × 6 machines to 100 jobs × 20 machines.

Instance files support two formats auto-detected by the parser:
- **OR-Library format** (ft, abz, la, orb, swv, yn): interleaved `<machine> <duration>` pairs per line
- **Taillard format** (ta): separate blocks for machine order and processing times

---

## Results Summary

| Algorithm | Avg Gap% | Min Gap% | Max Gap% | Avg Runtime | Wins |
|-----------|----------|----------|----------|-------------|------|
| MWKR | 57.57% | 5.42% | 124.29% | 0.02s | 0 |
| GA | 20.95% | 0.00% | 56.26% | 3.90s | 14 |
| Tabu Search | 3.63% | 0.00% | 30.83% | 2.90s | 64 |
| CP-SAT | 1.73% | 0.00% | 14.53% | 36.23s | 84 |

CP-SAT achieved **OPTIMAL** (proven) on 72 instances and **FEASIBLE** (60s timeout) on 90 instances.

### Key Findings

**Tabu Search is the best practical algorithm.** It achieves an average gap of 3.63%  within 4% of the best known solution on average  in under 3 seconds. For real-world production scheduling where time matters, Tabu Search offers the best quality-to-speed ratio.

**CP-SAT is the best overall but impractical for large instances.** It wins 84 of 162 instances but spends 60 seconds on most large problems without proving optimality. It is the right choice only when runtime is not a constraint and instance size is moderate (≤ 20 jobs).

**GA underperforms Tabu Search on JSSP.** Despite being a global search method, GA achieves only 20.95% average gap versus Tabu's 3.63%. This is consistent with the JSP literature  the problem's neighbourhood structure is better exploited by trajectory-based search.

**MWKR is fast but weak.** At 57.57% average gap it is far from competitive on quality, but its 0.02s runtime makes it the only viable option for real-time scheduling applications.

---

## How to Run

### 1. Install dependencies

```bash
pip install ortools pandas matplotlib numpy
```

### 2. Run the full benchmark

```bash
python main.py
```

Reads all instance files from `data/taillard_dataset/instances/` and writes results to `results/benchmark_results.csv`. Expected runtime: 2–4 hours on a modern laptop (dominated by CP-SAT's 60s timeout on large instances).

### 3. Generate visualisations

```bash
python visualize_benchmark.py
```

Reads `results/benchmark_results.csv` and saves 6 plots to `results/plots/`:

| Plot | Description |
|------|-------------|
| `gap_boxplot.png` | Optimality gap distribution per algorithm |
| `runtime_vs_gap.png` | Quality vs speed trade-off (log scale) |
| `scaling_jobs.png` | How gap% grows with number of jobs |
| `family_heatmap.png` | Per-instance-family performance heatmap |
| `cpsat_status.png` | CP-SAT OPTIMAL vs FEASIBLE breakdown by family |
| `win_rate.png` | Win rate per algorithm across all instances |

Custom CSV path:
```bash
python visualize_benchmark.py path/to/benchmark_results.csv
```

---

## CSV Column Reference

| Column | Type | Description |
|--------|------|-------------|
| `instance` | string | Instance filename stem (e.g. `ta01`, `la16`) |
| `num_jobs` | int | Number of jobs in the instance |
| `num_machines` | int | Number of machines in the instance |
| `algorithm` | string | `MWKR` / `GA` / `Tabu` / `CP-SAT` |
| `makespan` | int | Makespan achieved by the algorithm |
| `bks` | int | Best Known Solution from JSPLIB literature |
| `optimality_gap_pct` | float | `(makespan − bks) / bks × 100` |
| `runtime_s` | float | Wall-clock runtime in seconds (4 d.p.) |
| `status` | string | `OPTIMAL` / `FEASIBLE` / `HEURISTIC` / `NO_SOLUTION` |

---

## References

1. Fisher, H., & Thompson, G.L. (1963). Probabilistic learning combinations of local job-shop scheduling rules. *Factory Scheduling Conference, Carnegie Mellon University.*
2. Taillard, E. (1993). Benchmarks for basic scheduling problems. *European Journal of Operational Research, 64*(2), 278–285.
3. Nowicki, E., & Smutnicki, C. (1996). A fast taboo search algorithm for the job shop problem. *Management Science, 42*(6), 797–813.
4. Adams, J., Balas, E., & Zawack, D. (1988). The shifting bottleneck procedure for job shop scheduling. *Management Science, 34*(3), 391–401.
5. Panwalkar, S.S., & Iskander, W. (1977). A survey of scheduling rules. *Operations Research, 25*(1), 45–61.
6. Lawrence, S. (1984). *Resource constrained project scheduling: An experimental investigation of heuristic scheduling techniques.* Carnegie Mellon University.
7. Applegate, D., & Cook, W. (1991). A computational study of the job-shop scheduling problem. *ORSA Journal on Computing, 3*(2), 149–156.
8. Google OR-Tools CP-SAT Solver. https://developers.google.com/optimization
9. JSPLIB  JSP instance library. https://github.com/tamy0612/JSPLIB
