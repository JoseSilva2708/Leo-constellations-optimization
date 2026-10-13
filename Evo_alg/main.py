from NSGA2 import NSGA2
import os
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np


def main():

    problem = {
        "bounds": {
            "S": (10, 80),
            "P": (10, 80),
            "F": (0, 79),
            "inc": (40, 100),
            "h": (400, 2000)
        }
    }

    ideal_point = np.array([
        -2.0, # best possible coverage score
        problem["bounds"]["S"][0] * problem["bounds"]["P"][0] * 0.4 + problem["bounds"]["P"][0] * 30.0, # minimum cost
        13.64 # optimistic latency lower bound
    ], dtype=float)

    nadir_point = np.array([
        -1.74, # worst possible coverage score
        problem["bounds"]["S"][1] * problem["bounds"]["P"][1] * 0.4 + problem["bounds"]["P"][1] * 30.0,# maximum cost
        50.0 # conservative worst latency
    ], dtype=float)

    algorithm = NSGA2(
        p_crossover=0.8,
        p_mutation=0.3,
        ideal_point=ideal_point,
        nadir_point=nadir_point,
        max_iter=50,
        pop_size=100,
        eta_c=10,
        eta_m=10,
        verbose=True
    )

    final_population = algorithm.run(problem)

    fronts = algorithm.fast_non_dominated_sort(final_population)
    pareto_front = fronts[0]

    f1 = [ind.f[0] for ind in pareto_front if ind.feasible == True]
    f2 = [ind.f[1] for ind in pareto_front if ind.feasible == True]
    f3 = [ind.f[2] for ind in pareto_front if ind.feasible == True]

    os.makedirs("output_images", exist_ok=True)
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    ax.scatter(f1, f2, f3, c='red', s=60, alpha=0.7)
    ax.set_xlabel("Coverage (negated)", fontsize=12)
    ax.set_ylabel("Cost (sats)", fontsize=12)
    ax.set_zlabel("Latency (ms)", fontsize=12)

    plt.title("NSGA-II Final Pareto Front\n(Coverage-Cost-Latency)", fontsize=14, pad=20)
    
    #Seaborn -> VER!!!!
    plt.savefig('output_images/pareto_3d_final.png', dpi=300, bbox_inches='tight')
    plt.savefig('output_images/pareto_3d_final.pdf', bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    main()