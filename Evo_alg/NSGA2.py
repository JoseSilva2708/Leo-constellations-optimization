import random
from Constellation import Constellation
from skyfield.api import EarthSatellite, load
from pymoo.indicators.hv import Hypervolume
import numpy as np
from itertools import product
import logging

#For logging
import csv
import os
from statistics import mean, stdev

logging.basicConfig(
    filename="nsga2.log",
    filemode="w",
    level=logging.INFO,
    format="%(message)s",
)

HV_history = []

# ===============================
# Individual Structure
# ===============================

class Individual:
    def __init__(self, x):
        self.x = x
        self.f = None
        self.rank = None
        self.crowding_distance = 0
        self.extras = []
        self.feasible = True


class NSGA2:
    """
    Class that represents the evolutionary algorithm to solve the problem
    """
    def __init__(self, p_crossover, p_mutation,ideal_point, nadir_point, max_iter=50, pop_size=50, eta_c=20, eta_m=20, verbose=True):
        self.max_iter = max_iter
        self.pop_size = pop_size
        self.p_crossover = p_crossover
        self.p_mutation = p_mutation
        self.eta_c = eta_c
        self.eta_m = eta_m
        self.verbose = verbose
        self.log_dir = "nsga2_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.hv_ideal = np.array(ideal_point, dtype=float)
        self.hv_nadir = np.array(nadir_point, dtype=float)
        self.hv_metric = Hypervolume(
            ref_point=np.array([1, 1, 1], dtype=float),
            norm_ref_point=False,
            zero_to_one=True,
            ideal=self.hv_ideal,
            nadir=self.hv_nadir
        )

        self.hv_history = []
   
   
   
    # ===============================================================================
    # LOG GENERATION
    # ===============================================================================
    
    def log_generation(self, population, gen):
        """
        Method that generates detailed logs for each generation and also a log for overall population generations
        
        :param self: Self
        :param population: Set of individuals from certain generation
        :param gen: Number of generation
        """

        csv_file = os.path.join(self.log_dir, f"gen_{gen:03d}_population.csv")
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ind_id', 'S', 'P', 'F','angle', 'inc', 'h', 
                            'coverage', 'cost', 'e2e latency','one way latency', 'std latency','k-fold','mbe', 'rank', 'crowding'])
            
            for i, ind in enumerate(population):
                writer.writerow([i, *ind.x, *ind.f, ind.f[2]/2, *ind.extras, ind.rank, ind.crowding_distance])
        

        stats = self.compute_population_stats(population, gen)
        
        stats_file = os.path.join(self.log_dir, "population_stats.csv")
        file_exists = os.path.isfile(stats_file)
        
        with open(stats_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['gen', 'mean_cov', 'mean_cost', 'mean_lat',
                            'std_cov', 'std_cost', 'std_lat',
                            'best_cov', 'best_cost', 'best_lat',
                            'worst_cov', 'worst_cost', 'worst_lat',
                            'pareto_front_size','feasible_pareto_size',
                            'num_feasible', 'feasible_ratio',
                            'hypervolume'])
            
            writer.writerow(stats)
        
        if self.verbose:
            print(f"Gen {gen:03d}: {stats[1]:.4f}% mean cov, {stats[2]:.0f} mean cost, "
                f"{stats[3]:.4f}ms mean latency | Hypervolume: {stats[-1]}")


    def compute_hypervolume(self, population):
        F = np.array([ind.f for ind in population if ind.rank == 0 and ind.feasible == True], dtype=float)

        if len(F) == 0:
            return 0.0
        
        F_norm = (F - self.hv_ideal) / (self.hv_nadir - self.hv_ideal)
        #print("F raw:\n", F)
        #print("F norm:\n", F_norm)
        #print("max per objective:", np.max(F_norm, axis=0))
        #print("ref_point:", self.hv_metric.ref_point)

        return float(self.hv_metric.do(F))

    def compute_population_stats(self, population, gen):
        """
        Auxiliar function that calculates the stats of the metrics for every generation and the number of pareto individuals (min, max, mean, deviation)
        
        :param self: Self
        :param population: Set of individuals from certain generation
        :param gen: Number of generation
        
        :returns: Array with:
            - Number of generation;
            - For the 3 metrics:
                - Mean;
                - Best values;
                - Worst values;
            - Pareto size.
        """
        feasible = [ind for ind in population if ind.feasible == True]
        
        if len(feasible) >=2:
            
            coverages = [ind.f[0] for ind in feasible]
            costs = [ind.f[1] for ind in feasible]
            latencies = [ind.f[2] for ind in feasible]
        
            # Average for each metric
            mean_cov = mean(coverages)
            mean_cost = mean(costs)
            mean_lat = mean(latencies) if latencies else 1e9
            
            # Standard Deviation for each metric
            std_cov = stdev(coverages)
            std_cost = stdev(costs)
            std_lat = stdev(latencies)
            
            # Best and worst values for each metric
            # Worst
            max_cov = max(coverages)
            
            # Best
            min_cov = min(coverages)
            
            max_cost = max(costs)
            min_cost = min(costs)
            
            max_lat = max(latencies) if latencies else 1e9
            min_lat = min(latencies) if latencies else 1e9
            
            pareto_size = len([ind for ind in population if ind.rank == 0])
            
            feasible_pareto_size = len([ind for ind in population if ind.rank == 0 and ind.feasible == True])

            hv_value = self.compute_hypervolume(population)
            hv_norm = hv_value / np.prod(self.hv_metric.ref_point)
            

            num_feasible = len(feasible)
            feasible_ratio = num_feasible / len(population) if population else 0.0
            
        else:
            mean_cov = 0.0
            mean_cost = 0.0
            mean_lat = 1e9

            std_cov = 0.0
            std_cost = 0.0
            std_lat = 0.0

            min_cov = 0.0
            min_cost = 0.0
            min_lat = 1e9

            max_cov = 0.0
            max_cost = 0.0
            max_lat = 1e9

            hv_norm = 0.0
            pareto_size=0
            feasible_pareto_size=0
            num_feasible=0
            feasible_ratio=0
            
        self.hv_history.append(hv_norm)
        
        return [
            gen,
            mean_cov, mean_cost, mean_lat,
            std_cov, std_cost, std_lat,
            min_cov, min_cost, min_lat,
            max_cov, max_cost, max_lat,
            pareto_size,feasible_pareto_size,
            num_feasible, feasible_ratio,
            hv_norm
        ]



    def add_base_constellations(self, population):
        base_constellations = []
        
        #StarLink
        individual_StarLink_shell1 = Individual([22, 72, 17, 360, 53, 550])
        individual_StarLink_shell2 = Individual([22, 72, 17, 360, 53.2, 540])
        individual_StarLink_shell3 = Individual([58, 6, 0, 180, 97.6, 560])
        individual_StarLink_shell4 = Individual([20, 36, 0, 180, 97.6, 560])
        
        #Amazon
        individual_Kuiper_shell1 = Individual([34, 34, 11, 360, 51.9, 630])
        individual_Kuiper_shell2 = Individual([36, 36, 11, 360, 42.0, 610])
        individual_Kuiper_shell3 = Individual([28, 28, 11, 360, 33.0, 590])
        
        #GW
        individual_GW_A59shell3 = Individual([50, 40, 0,360, 50, 600])
        individual_GW_A59shell2 = Individual([30, 16, 0, 180, 85, 590])
        
        #Telesat
        individual_Telesat_shell1 = Individual([33, 40, 0, 360, 50.88, 1325])
        individual_Telesat_shell2 = Individual([13, 27, 0, 180, 98.98, 1015])
        
        #OneWeb
        individual_OneWeb_shell1 = Individual([49, 36, 0, 180, 87.9, 1200])
        individual_OneWeb_shell2 = Individual([72, 32, 0, 360, 55, 1200])
        individual_OneWeb_shell3 = Individual([72, 32, 0, 360, 40, 1200])
        
        
        
        base_constellations.append(individual_StarLink_shell1)
        base_constellations.append(individual_StarLink_shell2)
        base_constellations.append(individual_StarLink_shell3)
        base_constellations.append(individual_StarLink_shell4)
        
        base_constellations.append(individual_Kuiper_shell1)
        base_constellations.append(individual_Kuiper_shell2)
        base_constellations.append(individual_Kuiper_shell3)
        
        base_constellations.append(individual_Telesat_shell1)
        base_constellations.append(individual_Telesat_shell2)
        
        base_constellations.append(individual_OneWeb_shell1)
        base_constellations.append(individual_OneWeb_shell2)
        base_constellations.append(individual_OneWeb_shell3)
        
        base_constellations.append(individual_GW_A59shell2)
        base_constellations.append(individual_GW_A59shell3)
        population = base_constellations
        
        return population, len(base_constellations)
        

    def initialize_population(self, bounds):
        """
        Function that is responsible for creating the inicial population, by randomly setting values of the parameters inside
        the limits of the bounds
        
        :param self: Self
        :param bounds: Bounds of the parameters established in the begginning of the problem
        
        returns: List that represents the initial population, containning objects of the  class "Individual". Each one of these objects
        represents an individual with values of parameters, fitness, dominance rank and crowding distance.
        """
        population = []
        population, num_base_constellations = self.add_base_constellations(population)

        for _ in range(num_base_constellations, self.pop_size):
            
            S = random.randint(*bounds["S"])
            P = random.randint(*bounds["P"])
            
            
            F = random.randint(0, P - 1)
                
            inc = round(random.uniform(*bounds["inc"]), 4)
            h = round(random.uniform(*bounds["h"]), 4)
            angle = self.compute_angle(inc)
            
            individual = Individual([S, P, F, angle, inc, h])
            population.append(individual)
            
        if self.verbose:
            print("Initial population created.")
        
        return population
    
    
    def evaluate_population(self, population, times, grid_points,timescale, min_elev):
        """
        Function that is responsible for evaluating each individual of the population, by computing
        the three objective metrics: coverage, cost and latency. Each individual's fitness vector is
        updated in-place after evaluation.

        Coverage is computed as the combination of two metrics (k-fold coverage and minimum
        beam elevation), normalized and negated so that the problem becomes a minimization.
        Cost represents the total number of satellites in the constellation (S * P).
        Latency represents the estimated end-to-end propagation delay in milliseconds.

        :param self: Self
        :param population: List of Individual objects representing the current population to evaluate
        :param times: Skyfield time array defining the simulation time window
        :param grid_points: List of (lat, lon) tuples representing the Earth surface grid for coverage analysis
        :param timescale: Skyfield Timescale object used to generate satellite positions
        :param min_elev: Minimum elevation angle (degrees) for a satellite to be considered visible from a ground point
        """
        #DEBUG
        i = 0
        for individual in population:
            
            S, P, F, angle, inc, h = individual.x
            k = 2
            constellation = Constellation(S, P, F, inc, h, angle)
            

            tle_pairs = constellation.generate_tles(S, P, F, angle,  inc, h)
                
            satellites = [EarthSatellite(l1, l2, f"SAT-{i}", timescale) for i, (l1, l2) in enumerate(tle_pairs)]
            
            kfold, mbe = constellation.get_coverage(satellites, times, grid_points, min_elev, K=k)
            cost = int(constellation.get_cost())
            e2e_latency, std_latency = constellation.get_latency(timescale, satellites)
            e2e_latency = round(e2e_latency,4)
            std_latency = round(std_latency,4)
            
            lat_ok = e2e_latency <= 50
            cov_ok = (kfold >= 90 and mbe >= 75)

            individual.feasible = lat_ok and cov_ok

            if not lat_ok:
                e2e_latency = 1e9
                std_latency = 0.00

            if not cov_ok:
                coverage = 0.00
            else:
                coverage = round(-((kfold / 100.0) + (mbe / 90.0)), 4)
            
            #Memory optimization 
            del tle_pairs
            del satellites
            del constellation
            
            individual.f = [coverage, cost, e2e_latency]
            individual.extras = [std_latency, kfold, mbe]
            
            #DEBUG
            i+=1
            if self.verbose:
                logging.info(f"Individual {i}: Feasible:{individual.feasible}")
                logging.info(f"h = {h:.2f} km")
                logging.info(f"S={S} P={P} F={F} angle={angle} inc:{inc:.2f}")
                logging.info(f"{coverage:0.2f} ({kfold:0.2f} with K={k} and {mbe:0.2f}) {P * S}sats {cost}cost($) {e2e_latency:0.2f} ms\n")
        

    def write_individuos_file(self, population, filepath="individuos.txt", only_pareto=True):
        """
        Escreve os parâmetros das constelações para um ficheiro CSV simples:
        S,P,F,inc,h

        - inc é escrito com 2 casas decimais
        - h é convertido de km para metros
        - se only_pareto=True, escreve apenas os indivíduos da frente de Pareto
        """

        individuals_to_write = population

        if only_pareto:
            individuals_to_write = [ind for ind in population if ind.rank == 0]

        if not individuals_to_write:
            raise RuntimeError("Não há indivíduos para escrever em individuos.txt")


        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["S", "P", "F", "inc", "h"])

            for ind in individuals_to_write:
                S, P, F,angle, inc, h_km = ind.x
                h_m = int(round(h_km * 1000))

                writer.writerow([
                    int(S),
                    int(P),
                    int(F),
                    round(float(inc), 2),
                    h_m
                ])

        if self.verbose:
            print(f"Ficheiro de indivíduos escrito em: {filepath}")

    
    def run(self, problem):
        """
        Executes the Evolutionary Algorithm optimization loop over a fixed number of generations.

        The algorithm follows the standard NSGA-II pipeline:
        1. Initialize a random population within the given parameter bounds.
        2. Evaluate the metrics of each individual (coverage, cost, latency). The fitness is only coverage and cost
        3. For each generation:
            a. Perform fast non-dominated sorting to rank individuals into Pareto fronts.
            b. Compute crowding distance within each front to preserve diversity.
            c. Generate offspring via tournament selection, crossover, and mutation.
            d. Evaluate offspring fitness.
            e. Select the next generation from the combined parent + offspring pool
            using non-domination rank and crowding distance as selection criteria.
            f. Log generation statistics.

        The constellation search space is defined by the bounds in "problem", covering
        the Walker parameters S (satellites per plane), P (number of planes), F (phasing
        factor), inc (inclination) and h (altitude). Coverage is evaluated over a
        latitude/longitude grid at hourly intervals over a 50-hour window. Latency is
        evaluated as the mean propagation delay over one full orbital period.

        :param problem: Dictionary with key "bounds", mapping each parameter name
                        (S, P, F, inc, h) to a (min, max) tuple defining the search space.

        :returns: Final population after "max_iter" generations, sorted by
                non-domination rank.
        """
        
        bounds = problem["bounds"]
    
        #Initialize population
        population = self.initialize_population(bounds)
        
        
        lats = np.arange(-60, 61, 4) # Usar 1-4 para produção e 5-15 para debug
        lons = np.arange(-180, 181, 4) # Usar 1-4 para produção e 5-15 para debug
        grid_points = list(product(lats, lons))
        min_elev = 25
        ts = load.timescale()
        times = ts.utc(2000, 1, 1, np.arange(0, 50))
        
        
        # Calculate fitness of initial population
        self.evaluate_population(population, times, grid_points, ts, min_elev)
        
        for gen in range(self.max_iter):
            convergence = False
            fronts = self.fast_non_dominated_sort(population)   
              
            for front in fronts:
                self.crowding_distance(front)
                
            offspring = self.make_offspring(population, bounds)
            
            self.evaluate_population(offspring, times, grid_points, ts, min_elev)
            
            population = self.environmental_selection(population + offspring)
            
            
            self.log_generation(population, gen)
            
            
            if self.verbose:
                print(f"Generation {gen+1} completed.")
                
            # Convergence
            if len(self.hv_history) >= 10:
                window = self.hv_history[-10:]
                spread = max(window) - min(window)

                if spread <= 2e-3:
                    print(f"Convergence detected at generation {gen}")
                    convergence = True
            
            if gen == self.max_iter - 1 or convergence:
                self.write_individuos_file(
                    population,
                    filepath="individuos.txt",
                    only_pareto=True
                )
                break
                    
        return population
            
            
    # ==========================================
    # DOMINANCE
    # ==========================================
    def dominates(self, ind_1, ind_2):
        """
        Auxiliar function that verifies dominance between 2 individuals. It checks if one of the individuals is parcially better
        or absolut better than the other
        
        :param ind_1: First individual
        :param ind_2: Second individual
        """
        if ind_1.feasible and not ind_2.feasible:
            return True
        if not ind_1.feasible and ind_2.feasible:
            return False
        if not ind_1.feasible and not ind_2.feasible:
            return False
        
        better_or_equal = all(pi <= qi for pi, qi in zip(ind_1.f, ind_2.f))
        strictly_better = any(pi < qi for pi, qi in zip(ind_1.f, ind_2.f))
        return better_or_equal and strictly_better




    def fast_non_dominated_sort(self, population):
        """
        Function that sorts the entire population into Pareto fronts based on dominance relations.

        For each individual, it computes two values:
        - dom_set: the list of individuals that it dominates
        - dom_count: the number of individuals that dominate it

        Individuals with dom_count == 0 belong to the first front (rank 0). For each subsequent
        front, the dom_count of dominated individuals is decremented, and those that reach 0
        are assigned to the next front. This process repeats until all individuals are ranked.

        :param self: Self
        :param population: List of Individual objects to be sorted. Each individual must have
                        a valid .f attribute (fitness vector) with at least 2 objectives.

        returns: List of fronts, where each front is a list of Individual objects sharing the
                same dominance rank. fronts[0] contains the non-dominated Pareto-optimal
                individuals (rank 0), fronts[1] the next best, and so on.
        """
        fronts = [[]]
        for individual1 in population:
            individual1.dom_count = 0
            individual1.dom_set = []

            for individual2 in population:
                if self.dominates(individual1, individual2):
                    individual1.dom_set.append(individual2)
                elif self.dominates(individual2, individual1):
                    individual1.dom_count += 1

            if individual1.dom_count == 0:
                individual1.rank = 0
                fronts[0].append(individual1)

        i = 0
        while fronts[i]:
            next_front = []
            for p in fronts[i]:
                for q in p.dom_set:
                    q.dom_count -= 1
                    if q.dom_count == 0:
                        q.rank = i + 1
                        next_front.append(q)
            i += 1
            fronts.append(next_front)

        fronts.pop()
        return fronts


    def remove_duplicates(self, population):
        seen = set()
        unique = []

        for ind in population:
            key = (
                int(ind.x[0]), int(ind.x[1]), int(ind.x[2]), int(ind.x[3]),
                round(float(ind.x[4]), 2), round(float(ind.x[5]), 2) 
            )
            if key not in seen:
                seen.add(key)
                unique.append(ind)

        return unique

    # ==========================================
    # CROWDING DISTANCE
    # ==========================================
    def crowding_distance(self, front):
        n = len(front)

        if n == 0:
            return
        if n <= 2:
            for ind in front:
                ind.crowding_distance = float("inf")
            return

        for ind in front:
            ind.crowding_distance = 0.0

        counts = {}
        for ind in front:
            key = tuple(round(v, 8) for v in ind.f)
            counts[key] = counts.get(key, 0) + 1

        for m in range(3):
            front.sort(key=lambda ind: ind.f[m])

            front[0].crowding_distance = float("inf")
            front[-1].crowding_distance = float("inf")

            f_min = front[0].f[m]
            f_max = front[-1].f[m]
            denom = f_max - f_min

            if denom == 0:
                continue

            for i in range(1, n - 1):
                if np.isinf(front[i].crowding_distance):
                    continue
                front[i].crowding_distance += (front[i + 1].f[m] - front[i - 1].f[m]) / denom

        for ind in front:
            key = tuple(round(v, 8) for v in ind.f)
            if counts[key] > 1 and not np.isinf(ind.crowding_distance):
                ind.crowding_distance = 0.0


    def compute_angle(self, inc):
        return 180 if inc >= 75 else 360

    # ==========================================
    # SELECTION
    # ==========================================
    def tournament(self, population):
        """
        Function that is responsible for the selection part: This function selects randomly 2 parents from the population and does a 
        tournament between those parents. If the rank of parent A is better than parent B, select parent A.
        Otherwise, select Parent B.
        If Both parents have the same rank, selects the parent with higher crowdind_distance to achieve a better population diversity. 
        
        :param self: Self class
        :param population: Population that is being evaluated
        """
        a, b = random.sample(population, 2)

        if a.rank < b.rank:
            return a
        elif a.rank > b.rank:
            return b
        else:
            return a if a.crowding_distance > b.crowding_distance else b


    # ==========================================
    # OFFSPRING
    # ==========================================
    def make_offspring(self, population, bounds):  
        """
        Generate the offspring population for the next generation.

        This method applies the standard genetic operators used in NSGA-II.
        Parents are selected from the current population using tournament
        selection. With a given crossover probability, their decision variables
        are recombined to produce two offspring solutions. Otherwise, the
        offspring are simple copies of the parents. Mutation is then applied
        to each offspring to introduce additional diversity.

        The process repeats until the desired population size is reached.

        Parameters:
            - population : Current population of individuals from which parents are selected.
                        Each individual contains the decision variables and attributes
                        such as rank and crowding distance used during tournament selection.

            - bounds : Lower and upper bounds for each decision variable. These bounds
                        are used by the crossover and mutation operators to ensure that
                        generated solutions remain within the feasible search space.

        Returns:
            - A list of newly created individuals representing the offspring
                population. The size of the returned list is equal to `self.pop_size`.
                The offspring are not yet evaluated (objective values are assigned
                later in the evaluation phase).
        """
        
        offspring = []

        while len(offspring) < self.pop_size:

            parent1 = self.tournament(population)
            parent2 = self.tournament(population)

            if random.random() < self.p_crossover:
                child1_x, child2_x = self.crossover(parent1.x, parent2.x, bounds)
            else:
                child1_x = parent1.x[:]
                child2_x = parent2.x[:]

            child1_x = self.mutation(child1_x, bounds)
            child2_x = self.mutation(child2_x, bounds)

            child1 = Individual(child1_x)
            child2 = Individual(child2_x)

            
            if self.verbose:
                print("\n==============================")
                print("PARENTS:")
                print(f"P1 x = {parent1.x} | rank={parent1.rank} | crowd={parent1.crowding_distance}")
                print(f"P2 x = {parent2.x} | rank={parent2.rank} | crowd={parent2.crowding_distance}")

                print("\nCHILDREN (before evaluation):")
                print(f"C1 x = {child1.x}")
                print(f"C2 x = {child2.x}")

            offspring.append(child1)
            offspring.append(child2)

        return offspring[:self.pop_size]


    # ==========================================
    # CROSSOVER
    # ==========================================

    def crossover(self, x1, x2, bounds):
        """
        x = [S, P, F, inc, h]
        índices 0-3: discretos/inteiros
        índices 4-5: contínuos
        """

        # Discrete/int crossover on [S, P, F, angle]
        cut1, cut2 = sorted(random.sample(range(4), 2))

        child1 = x1[:4]
        child2 = x2[:4]

        child1[cut1:cut2] = x2[cut1:cut2]
        child2[cut1:cut2] = x1[cut1:cut2]
        
        child1[3] = x1[3]
        child2[3] = x2[3]

        # SBX for continuous [inc, h]
        for i in [4, 5]:
            if random.random() <= 0.5:
                beta = self.compute_beta()
                c1 = 0.5 * ((1 + beta) * x1[i] + (1 - beta) * x2[i])
                c2 = 0.5 * ((1 - beta) * x1[i] + (1 + beta) * x2[i])
            else:
                c1, c2 = x1[i], x2[i]

            key = "inc" if i == 4 else "h"
            lb, ub = bounds[key]

            c1 = round(min(max(c1, lb), ub), 4)
            c2 = round(min(max(c2, lb), ub), 4)

            child1.append(c1)
            child2.append(c2)

        # Structural constraint
        if child1[2] >= child1[1]:
            child1[2] = random.randint(0, child1[1] - 1)

        if child2[2] >= child2[1]:
            child2[2] = random.randint(0, child2[1] - 1)

        return child1, child2


    def compute_beta(self):
        """
        Samples the spread factor "beta" for the Simulated Binary Crossover (SBX)
        operator from the polynomial probability distribution.

        The distribution is parameterized by "eta_c" (crossover distribution index),
        which controls the spread of offspring relative to parents:
        - Low "eta_c" (e.g. 2): offspring spread far from parents (exploratory)
        - High "eta_c" (e.g. 20): offspring stay close to parents (exploitative)

        :returns: Spread factor "beta" sampled from the SBX polynomial distribution.
        :rtype: float
        """
        
        u = random.random()
        if u <= 0.5:
            return (2*u)**(1/(self.eta_c+1))
        else:
            return (1/(2*(1-u)))**(1/(self.eta_c+1))


    # ==========================================
    # MUTATION
    # ==========================================
    def mutation(self, x, bounds):
        """
        x = [S, P, F, angle, inc, h]
        """

        # Integer mutation for S, P, F
        for i, key in zip([0, 1, 2], ["S", "P", "F"]):
            if random.random() < self.p_mutation:
                lb, ub = bounds[key]
                step = max(1, int(0.2 * (ub - lb)))
                x[i] += random.randint(-step, step)
                x[i] = min(max(x[i], lb), ub)

        # Keep Walker constraint
        P, F = x[1], x[2]
        if F >= P:
            x[2] = random.randint(0, P - 1)

        # Polynomial mutation for continuous [inc, h]
        for i in [4, 5]:
            if random.random() < self.p_mutation:
                u = random.random()
                delta = (2 * u) ** (1 / (self.eta_m + 1)) - 1 if u < 0.5 \
                    else 1 - (2 * (1 - u)) ** (1 / (self.eta_m + 1))

                key = "inc" if i == 4 else "h"
                lb, ub = bounds[key]

                x[i] += delta * (ub - lb)
                x[i] = round(min(max(x[i], lb), ub), 4)
        
        x[3] = self.compute_angle(x[4])
        
        return x
    

    # ==========================================
    # ENVIRONMENTAL SELECTION
    # ==========================================

    def environmental_selection(self, population):
        """
        Selects the next generation population from the combined parent and offspring pool
        using NSGA-II's elitist selection strategy.

        Individuals are first ranked into Pareto fronts via fast non-dominated sorting.
        Fronts are then added to the new population in order of increasing rank until
        the population size limit is reached. If a front cannot be added in full, its
        individuals are sorted by crowding distance (descending) and only the best are
        taken to fill the remaining slots.

        This ensures that:
        - Lower-rank (better) fronts are always preferred over higher-rank fronts.
        - Within the same front, more isolated individuals (higher crowding distance)
        are preferred to maintain diversity along the Pareto front.

        :param population: Combined list of parent and offspring individuals.
        
        :returns: New population of exactly "pop_size" individuals selected by
                non-domination rank and crowding distance.
        """
        population = self.remove_duplicates(population)
        new_population = []
        fronts = self.fast_non_dominated_sort(population)

        for front in fronts:
            self.crowding_distance(front)
            front.sort(key=lambda x: (x.rank, -x.crowding_distance))

            if len(new_population) + len(front) <= self.pop_size:
                new_population.extend(front)
            else:
                needed = self.pop_size - len(new_population)
                new_population.extend(front[:needed])
                break

        return new_population
    