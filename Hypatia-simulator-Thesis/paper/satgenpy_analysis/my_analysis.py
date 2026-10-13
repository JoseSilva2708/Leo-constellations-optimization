import exputil
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--num-sats", required=True, type=int)
args = parser.parse_args()

local_shell = exputil.LocalShell()
max_num_processes = 6

if local_shell.count_screens() != 0:
    print("There is a screen already running. Please kill all screens before running this analysis script (killall screen).")
    exit(1)

local_shell.remove_force_recursive("data")
local_shell.make_full_dir("data")
local_shell.make_full_dir("data/command_logs")

commands_to_run = []

# ===== CUSTOM CONFIG =====
SCENARIO_DIR = "my_walker_test_isls_plus_grid_ground_stations_algorithm_free_one_only_over_isls"
UPDATE_INTERVAL_MS = 225000
DURATION_S = 5400
NUM_SATS = args.num_sats

GROUND_STATIONS = {
    "Lisbon": 0,
    "Rome": 1,
    "Berlin": 2,
    "Moscow": 3,
    "Chicago": 4,
    "Miami": 5,
    "London": 6,
    "Tokyo": 7,
    "Shanghai": 8,
}

GROUND_PAIRS = [
    ("Lisbon", "Rome", "lisbon_rome"),
    ("Berlin", "Moscow", "berlin_moscow"),
    ("Chicago", "Miami", "chicago_miami"),
    ("London", "Rome", "london_rome"),
    ("Tokyo", "Shanghai", "tokyo_shanghai"),
]

def endpoint_id(gs_name):
    return NUM_SATS + GROUND_STATIONS[gs_name]

print("Generating commands for manually selected endpoint pairs...")

for src, dst, label in GROUND_PAIRS:
    src_id = endpoint_id(src)
    dst_id = endpoint_id(dst)

    commands_to_run.append(
        "cd ../../satgenpy; python -m satgen.post_analysis.main_print_routes_and_rtt "
        "../paper/satgenpy_analysis/data "
        "../paper/satellite_networks_state/gen_data/%s "
        "%d %d %d %d "
        "> ../paper/satgenpy_analysis/data/command_logs/manual_%s.log 2>&1"
        % (
            SCENARIO_DIR,
            UPDATE_INTERVAL_MS,
            DURATION_S,
            src_id,
            dst_id,
            label
        )
    )

    commands_to_run.append(
        "cd ../../satgenpy; python -m satgen.post_analysis.main_print_graphical_routes_and_rtt "
        "../paper/satgenpy_analysis/data "
        "../paper/satellite_networks_state/gen_data/%s "
        "%d %d %d %d "
        "> ../paper/satgenpy_analysis/data/command_logs/manual_graphical_%s.log 2>&1"
        % (
            SCENARIO_DIR,
            UPDATE_INTERVAL_MS,
            DURATION_S,
            src_id,
            dst_id,
            label
        )
    )

print("Generating commands for constellation analysis...")

commands_to_run.append(
    "cd ../../satgenpy; python -m satgen.post_analysis.main_analyze_path "
    "../paper/satgenpy_analysis/data "
    "../paper/satellite_networks_state/gen_data/%s %d %d "
    "> ../paper/satgenpy_analysis/data/command_logs/constellation_path.log 2>&1"
    % (SCENARIO_DIR, UPDATE_INTERVAL_MS, DURATION_S)
)

commands_to_run.append(
    "cd ../../satgenpy; python -m satgen.post_analysis.main_analyze_rtt "
    "../paper/satgenpy_analysis/data "
    "../paper/satellite_networks_state/gen_data/%s %d %d "
    "> ../paper/satgenpy_analysis/data/command_logs/constellation_rtt.log 2>&1"
    % (SCENARIO_DIR, UPDATE_INTERVAL_MS, DURATION_S)
)

print("Running commands (at most %d in parallel)..." % max_num_processes)
for i in range(len(commands_to_run)):
    print("Starting command %d out of %d: %s" % (i + 1, len(commands_to_run), commands_to_run[i]))
    local_shell.detached_exec(commands_to_run[i])
    while local_shell.count_screens() >= max_num_processes:
        time.sleep(2)

print("Waiting completion of the last %d..." % max_num_processes)
while local_shell.count_screens() > 0:
    time.sleep(2)

print("Finished.")
