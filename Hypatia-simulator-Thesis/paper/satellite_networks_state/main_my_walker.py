import math
import argparse
from main_helper import MainHelper

EARTH_RADIUS = 6378135.0
ECCENTRICITY = 0.0000001
ARG_OF_PERIGEE_DEGREE = 0.0
PHASE_DIFF = True

BASE_NAME = "my_walker_test"
NICE_NAME = "my-walker-test"

mu = 3.986004418e14
R_earth = 6378135.0

def build_main_helper(num_orbs, num_sats_per_orb, phase, inclination_degree, altitude_m):
    r = R_earth + altitude_m
    n_rad_s = math.sqrt(mu / r**3)
    mean_motion_rev_per_day = n_rad_s * 86400 / (2 * math.pi)

    satellite_cone_radius_m = altitude_m / math.tan(math.radians(30.0))
    max_gsl_length_m = math.sqrt(satellite_cone_radius_m**2 + altitude_m**2)
    max_isl_length_m = 2 * math.sqrt((EARTH_RADIUS + altitude_m)**2 - (EARTH_RADIUS + 80000)**2)

    return MainHelper(
        BASE_NAME,
        NICE_NAME,
        ECCENTRICITY,
        ARG_OF_PERIGEE_DEGREE,
        PHASE_DIFF,
        phase,
        mean_motion_rev_per_day,
        altitude_m,
        max_gsl_length_m,
        max_isl_length_m,
        num_orbs,
        num_sats_per_orb,
        inclination_degree,
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-orbs", required=True, type=int)
    parser.add_argument("--num-sats-per-orb", required=True, type=int)
    parser.add_argument("--phase", required=True, type=int)
    parser.add_argument("--inclination", required=True, type=float)
    parser.add_argument("--altitude-m", required=True, type=float)
    args = parser.parse_args()

    main_helper = build_main_helper(
        args.num_orbs,
        args.num_sats_per_orb,
        args.phase,
        args.inclination,
        args.altitude_m,
    )

    main_helper.calculate(
        "gen_data",
        5400,
        225000,
        "isls_plus_grid",
        "ground_stations",
        "algorithm_free_one_only_over_isls",
        4,
    )

if __name__ == "__main__":
    main()
