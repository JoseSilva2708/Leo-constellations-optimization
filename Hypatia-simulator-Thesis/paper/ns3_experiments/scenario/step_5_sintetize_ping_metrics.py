#!/usr/bin/env python3

import re
import csv
import argparse
from pathlib import Path
from statistics import mean

PING_LINE_RE = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+"
    r"([\d.]+)\s+ms\s+"
    r"([\d.]+)\s+ms\s+"
    r"([\d.]+)\s+ms\s+"
    r"([\d.]+)\s+ms\s+"
    r"([\d.]+)\s+ms\s+"
    r"([\d.]+)\s+ms\s+"
    r"(\d+)/(\d+)\s+\(([\d.]+)%\)\s*$"
)

def parse_pingmesh_txt(file_path: Path):
    lines = [line.rstrip("\n") for line in file_path.read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError(f"Ficheiro sem dados: {file_path}")

    data_line = lines[-1]
    m = PING_LINE_RE.match(data_line)
    if not m:
        raise ValueError(f"Formato inesperado em {file_path}: {data_line}")

    return {
        "min_rtt_ms": float(m.group(5)),
        "mean_rtt_ms": float(m.group(6)),
        "max_rtt_ms": float(m.group(7)),
        "std_rtt_ms": float(m.group(8)),
        "reply_received": int(m.group(9)),
        "reply_total": int(m.group(10)),
        "reply_percent": float(m.group(11)),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", default="runs", type=Path)
    parser.add_argument("--individuo-id", required=True, type=int)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    output_dir = args.output_root / f"individuo_{args.individuo_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "ping_rtt_summary.csv"

    rows = []

    for run_dir in sorted(args.runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        if not run_dir.name.endswith("_pings"):
            continue

        logs_dir = run_dir / "logs_ns3"
        pingmesh_file = logs_dir / "pingmesh.txt"

        if not pingmesh_file.exists():
            print(f"[WARN] Ficheiro em falta em {run_dir.name}")
            continue

        data = parse_pingmesh_txt(pingmesh_file)

        rows.append({
            "run_name": run_dir.name,
            "min_rtt_ms": data["min_rtt_ms"],
            "mean_rtt_ms": data["mean_rtt_ms"],
            "max_rtt_ms": data["max_rtt_ms"],
            "std_rtt_ms": data["std_rtt_ms"],
            "reply_received": data["reply_received"],
            "reply_total": data["reply_total"],
            "reply_percent": data["reply_percent"],
        })

    if not rows:
        raise RuntimeError("Nenhum ficheiro pingmesh.txt válido encontrado.")

    summary = {
        "run_name": "SUMMARY",
        "min_rtt_ms": mean(r["min_rtt_ms"] for r in rows),
        "mean_rtt_ms": mean(r["mean_rtt_ms"] for r in rows),
        "max_rtt_ms": mean(r["max_rtt_ms"] for r in rows),
        "std_rtt_ms": mean(r["std_rtt_ms"] for r in rows),
        "reply_received": sum(r["reply_received"] for r in rows),
        "reply_total": sum(r["reply_total"] for r in rows),
        "reply_percent": (
            sum(r["reply_received"] for r in rows) / sum(r["reply_total"] for r in rows) * 100.0
            if sum(r["reply_total"] for r in rows) > 0 else 0.0
        ),
    }

    with output_file.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "run_name",
                "min_rtt_ms",
                "mean_rtt_ms",
                "max_rtt_ms",
                "std_rtt_ms",
                "reply_received",
                "reply_total",
                "reply_percent",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(summary)

    print(f"Resumo escrito em: {output_file}")

if __name__ == "__main__":
    main()
