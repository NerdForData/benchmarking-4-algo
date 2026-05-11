import os
import sys
import random
from copy import deepcopy

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.schedule_builder import ScheduleBuilder
from benchmark.metrics import calculate_makespan


class GeneticAlgorithm:

    def __init__(self, instance, population_size=50, generations=100, mutation_rate=0.1):
        self.instance = instance
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate

    def _get_jobs(self):
        if isinstance(self.instance, dict):
            return self.instance.get("jobs", [])
        return getattr(self.instance, "jobs", [])

    def create_individual(self):
        """
        Create a random chromosome. Each gene is (job_id, operation_id, machine, duration).
        The chromosome is a permutation of all operations across all jobs — valid because
        ScheduleBuilder respects job_available constraints regardless of chromosome order.
        """
        operations = []
        for job_id, job in enumerate(self._get_jobs()):
            for operation_id, (machine, duration) in enumerate(job):
                operations.append((job_id, operation_id, machine, duration))
        random.shuffle(operations)
        return operations

    def build_schedule(self, chromosome):
        builder = ScheduleBuilder(self.instance)
        for job_id, operation_id, machine, duration in chromosome:
            builder.add_operation(job_id, operation_id, machine, duration)
        return builder.get_schedule()

    def fitness(self, chromosome):
        schedule = self.build_schedule(chromosome)
        return calculate_makespan(schedule)

    def _compute_fitness_cache(self, population):
        """
        Evaluate every individual exactly once and return a parallel list of fitness values.
        This prevents the original bug of calling self.fitness() 3+ times per individual
        per generation (selection sort + min() call = O(population^2 * generations) evals).
        """
        return [self.fitness(ind) for ind in population]

    def _tournament_select(self, population, fitness_cache, k=3):
        """
        Tournament selection: pick k random individuals, return the fittest.
        Much cheaper than sorting the whole population (original selection()).
        """
        indices = random.sample(range(len(population)), k)
        best_idx = min(indices, key=lambda i: fitness_cache[i])
        return population[best_idx]

    def crossover(self, parent1, parent2):
        """
        Order crossover (OX1) using (job_id, operation_id) as the unique key.

        FIX: the original used full 4-tuple gene equality for deduplication. If two
        operations share the same (machine, duration) — common in Taillard instances —
        the wrong gene could be silently dropped, producing invalid chromosomes. We now
        track membership strictly by (job_id, operation_id).
        """
        if len(parent1) <= 2:
            return deepcopy(parent1)

        point = random.randint(1, len(parent1) - 2)
        child = parent1[:point]

        # Track which (job, op) pairs are already in the child
        seen = {(g[0], g[1]) for g in child}

        # Fill remaining genes from parent2 in order, skipping already-placed ops
        remaining = [g for g in parent2 if (g[0], g[1]) not in seen]
        child.extend(remaining)

        return child

    def mutate(self, chromosome):
        """Swap mutation: randomly swap two genes with probability mutation_rate."""
        chromosome = deepcopy(chromosome)
        if random.random() < self.mutation_rate:
            i, j = random.sample(range(len(chromosome)), 2)
            chromosome[i], chromosome[j] = chromosome[j], chromosome[i]
        return chromosome

    def solve(self):
        population = [self.create_individual() for _ in range(self.population_size)]

        best_solution = None
        best_fitness = float("inf")

        for generation in range(self.generations):
            # Compute fitness once per individual per generation
            fitness_cache = self._compute_fitness_cache(population)

            # Track global best (elitism)
            gen_best_idx = min(range(len(population)), key=lambda i: fitness_cache[i])
            gen_best_fitness = fitness_cache[gen_best_idx]
            if gen_best_fitness < best_fitness:
                best_fitness = gen_best_fitness
                best_solution = deepcopy(population[gen_best_idx])

            # Build next generation
            new_population = []

            # Elitism: carry the best individual forward unchanged
            new_population.append(deepcopy(population[gen_best_idx]))

            while len(new_population) < self.population_size:
                parent1 = self._tournament_select(population, fitness_cache)
                parent2 = self._tournament_select(population, fitness_cache)
                child = self.crossover(parent1, parent2)
                child = self.mutate(child)
                new_population.append(child)

            population = new_population

        final_schedule = self.build_schedule(best_solution)
        return {
            "schedule": final_schedule,
            "makespan": calculate_makespan(final_schedule),
            "status": "HEURISTIC"
        }