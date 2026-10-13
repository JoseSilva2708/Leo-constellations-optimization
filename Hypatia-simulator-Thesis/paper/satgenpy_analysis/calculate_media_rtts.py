import os

base_dir = "/home/jose/Tese/hypatia/paper/satgenpy_analysis/data/my_walker_test_isls_plus_grid_ground_stations_algorithm_free_one_only_over_isls/225000ms_for_5400s/manual/data"

NUM_SATS = 720

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

MANUAL_PAIRS = [
    ("Lisbon_Rome", "Lisbon", "Rome"),
    ("Berlin_Moscow", "Berlin", "Moscow"),
    ("Chicago_Miami", "Chicago", "Miami"),
    ("London_Rome", "London", "Rome"),
    ("Tokyo_Shanghai", "Tokyo", "Shanghai"),
]

def endpoint_id(gs_name):
    return NUM_SATS + GROUND_STATIONS[gs_name]

all_rtts_ns = []
per_file_means = {}

for label, src_name, dst_name in MANUAL_PAIRS:
    src_id = endpoint_id(src_name)
    dst_id = endpoint_id(dst_name)

    filepath = os.path.join(base_dir, f"networkx_rtt_{src_id}_to_{dst_id}.txt")

    if not os.path.exists(filepath):
        print(f"[WARNING] File not found: {filepath}")
        continue

    vals = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            t_ns, rtt_ns = line.split(",")
            rtt_ns = float(rtt_ns)
            vals.append(rtt_ns)
            all_rtts_ns.append(rtt_ns)

    if vals:
        per_file_means[label] = sum(vals) / len(vals)

if not all_rtts_ns:
    print("No RTT samples found for manual pairs.")
    exit(1)

global_mean_ns = sum(all_rtts_ns) / len(all_rtts_ns)
global_mean_ms = global_mean_ns / 1e6

print("Manual pairs global mean RTT (all samples):", global_mean_ns, "ns")
print("Manual pairs global mean RTT (all samples):", global_mean_ms, "ms")

print("\nMean RTT per manual pair:")
for label, mean_ns in per_file_means.items():
    print(label, "->", mean_ns / 1e6, "ms")

mean_of_pair_means_ns = sum(per_file_means.values()) / len(per_file_means)
print("\nMean of manual-pair means:", mean_of_pair_means_ns / 1e6, "ms")
