import csv
import argparse
from pathlib import Path
from statistics import mean, stdev

BASE_DIR = Path("/home/admin/Tese/hypatia/paper/satgenpy_analysis/data/my_walker_test_isls_plus_grid_ground_stations_algorithm_free_one_only_over_isls/225000ms_for_5400s/manual/data")

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

def endpoint_id(num_sats, gs_name):
    return num_sats + GROUND_STATIONS[gs_name]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-sats", required=True, type=int)
    parser.add_argument("--individuo-id", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_root) / f"individuo_{args.individuo_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "rtt_summary.csv"

    rows = []
    all_rtts_ns = []
    missing_files = []

    for label, src_name, dst_name in MANUAL_PAIRS:
        src_id = endpoint_id(args.num_sats, src_name)
        dst_id = endpoint_id(args.num_sats, dst_name)

        filepath = BASE_DIR / f"networkx_rtt_{src_id}_to_{dst_id}.txt"
        if not filepath.exists():
            missing_files.append(str(filepath))
            continue

        vals_ns = []
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                _, rtt_ns = line.split(",")
                rtt_ns = float(rtt_ns)
                vals_ns.append(rtt_ns)
                all_rtts_ns.append(rtt_ns)

        if not vals_ns:
            continue

        mean_rtt_ms = mean(vals_ns) / 1e6
        std_rtt_ms = (stdev(vals_ns) / 1e6) if len(vals_ns) > 1 else 0.0

        rows.append({
            "label": label,
            "mean_rtt_ms": mean_rtt_ms,
            "std_rtt_ms": std_rtt_ms,
        })

    if not rows:
        raise RuntimeError(
            f"Nenhum ficheiro RTT válido encontrado para num_sats={args.num_sats} em {BASE_DIR}"
        )

    rows.append({
        "label": "SUMMARY",
        "mean_rtt_ms": mean(all_rtts_ns) / 1e6,
        "std_rtt_ms": "",
    })

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["label", "mean_rtt_ms", "std_rtt_ms"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"RTT summary escrito em: {output_file}")

    if missing_files:
        print("\n[WARNING] Alguns ficheiros RTT não foram encontrados:")
        for m in missing_files:
            print("  -", m)

if __name__ == "__main__":
    main()
