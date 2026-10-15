# LEO Constellation Optimization

This repository contains the framework developed for my Master's dissertation,
*Designing Satellite Constellations to Improve Network Usage*.

It uses an NSGA-II-inspired evolutionary algorithm to optimize Walker-based
LEO satellite constellations for a global broadband and low-latency Internet
scenario. Candidate constellations are evaluated according to coverage,
deployment cost, and propagation delay.

The best-performing configurations are then validated using Hypatia and ns-3,
which provide packet-level end-to-end network evaluation.

## How It Works

1. The evolutionary algorithm generates candidate Walker constellations.
2. Each candidate is evaluated for coverage, deployment cost, and propagation delay.
3. The algorithm evolves the population using selection, crossover, mutation,
   and Pareto-based environmental selection.
4. The resulting feasible Pareto-front constellations are exported.
5. The exported constellations are passed to the Hypatia/ns-3 workflow.
6. Hypatia generates the satellite network state and runs ns-3 simulations.
7. The results are used to validate propagation delay and assess end-to-end
   network performance.

## Repository Structure

```text
leo-constellation-optimization/
├── Evo_alg/
│   └── NSGA2.py
└── Hypatia-simulator-Thesis/
    ├── ns3-sat-sim/
    ├── satgenpy/
    ├── satviz/
    └── paper/
```

- `Evo_alg/` contains the evolutionary optimization framework.
- `Hypatia-simulator-Thesis/` contains the Hypatia/ns-3 simulation environment.

## Requirements

This project requires **Python 3.10**, which is the version used for the
Hypatia/ns-3 experimental setup.

Create and activate a virtual environment:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Running the Framework

The complete optimization and simulation workflow can be executed using:

```bash
./automate_scripts.sh
```

This script automates the main stages of the framework:

1. Runs the evolutionary optimization.
2. Exports the resulting constellation configurations.
3. Generates the corresponding Hypatia satellite network state.
4. Runs the ns-3 simulations.
5. Collects and organizes the simulation results.

Before running the script, ensure that the Hypatia dependencies and simulator
are installed. The Hypatia setup scripts are available in:

```bash
Hypatia-simulator-Thesis/hypatia_install_dependencies.sh
Hypatia-simulator-Thesis/hypatia_build.sh
```

The Hypatia build was adapted in this project to use an optimized ns-3 build:

```bash
bash build.sh optimized disable-werror
```

Refer to the documentation inside `Hypatia-simulator-Thesis/` for additional
system dependencies and build details.

## Constellation Parameters

Each candidate constellation is represented by:

```text
S, P, F, inc, h
```

Where:

- `S` is the number of satellites per orbital plane.
- `P` is the number of orbital planes.
- `F` is the Walker phasing factor.
- `inc` is the orbital inclination, in degrees.
- `h` is the orbital altitude, in kilometers.

The optimization seeks feasible trade-offs between these parameters rather
than a single optimal constellation.

## Optimization Objectives

The framework evaluates three objectives:

- **Coverage:** combines 2-fold coverage and Mean Best Elevation (MBE).
- **Deployment cost:** simplified cost model based on the number of satellites
  and orbital planes.
- **Propagation delay:** estimated round-trip propagation delay between
  selected ground-station pairs.

Candidate constellations that do not satisfy the coverage, elevation, delay,
or connectivity requirements are treated as infeasible.

## Outputs

The optimization exports the feasible Pareto-front constellations and
generation statistics. The exported constellation file uses the format:

```csv
S,P,F,inc,h
```

The Hypatia/ns-3 workflow produces results for propagation-delay validation,
end-to-end latency, and packet-level network performance.

## Technologies

- Python
- NumPy
- Matplotlib
- NetworkX
- Skyfield
- SGP4
- pymoo
- Hypatia
- ns-3

## Author

José Silva  
MSc in Informatics Engineering — Communications, Cloud and IoT  
University of Coimbra
