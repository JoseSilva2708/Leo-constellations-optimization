#!/usr/bin/env python3

import re
import csv
import argparse
from pathlib import Path
from statistics import mean

BASE_DIR_DEFAULT = Path("runs")


def parse_udp_burst_txt(file_path):
    lines = [line.rstrip("\n") for line in file_path.read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError(f"Ficheiro sem dados: {file_path}")

    data_line = lines[-1]
    cols = re.split(r"\s{2,}", data_line.strip())

    if len(cols) < 11:
        raise ValueError(f"Formato inesperado em {file_path}: {cols}")

    return {
        "udp_burst_id": int(cols[0]),
        "packets": int(cols[8]),
        "rate_with_headers_mbps": float(cols[6].replace(" Mbit/s", "")),
        "rate_payload_mbps": float(cols[7].replace(" Mbit/s", "")),
        "data_with_headers_mbit": float(cols[9].replace(" Mbit", "")),
        "data_payload_mbit": float(cols[10].replace(" Mbit", "")),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", default=BASE_DIR_DEFAULT, type=Path)
    parser.add_argument("--individuo-id", required=True, type=int)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    base_dir = args.runs_dir
    output_dir = args.output_root / f"individuo_{args.individuo_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "udp_summary.csv"

    rows = []

    for run_dir in sorted(base_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        if "_udp_at_" not in run_dir.name:
            continue

        logs_dir = run_dir / "logs_ns3"
        outgoing_file = logs_dir / "udp_bursts_outgoing.txt"
        incoming_file = logs_dir / "udp_bursts_incoming.txt"

        if not outgoing_file.exists() or not incoming_file.exists():
            print(f"[WARN] Ficheiros em falta em {run_dir.name}")
            continue

        out_data = parse_udp_burst_txt(outgoing_file)
        in_data = parse_udp_burst_txt(incoming_file)

        packets_sent = out_data["packets"]
        packets_received = in_data["packets"]
        packets_lost = packets_sent - packets_received
        loss_rate = (packets_lost / packets_sent) if packets_sent > 0 else 0.0

        throughput_payload_rate_mbps = in_data["rate_payload_mbps"]
        throughput_with_headers_rate_mbps = in_data["rate_with_headers_mbps"]
        throughput_payload_percent = (
            (in_data["rate_payload_mbps"] / out_data["rate_payload_mbps"]) * 100.0
            if out_data["rate_payload_mbps"] > 0 else 0.0
        )
        throughput_with_headers_percent = (
            (in_data["rate_with_headers_mbps"] / out_data["rate_with_headers_mbps"]) * 100.0
            if out_data["rate_with_headers_mbps"] > 0 else 0.0
        )

        rows.append({
            "run_name": run_dir.name,
            "packets_sent": packets_sent,
            "packets_received": packets_received,
            "packets_lost": packets_lost,
            "loss_rate": loss_rate,
            "loss_percent": loss_rate * 100.0,
            "throughput_with_headers_mbps": throughput_with_headers_rate_mbps,
            "throughput_payload_mbps": throughput_payload_rate_mbps,
            "throughput_with_headers_percent": throughput_with_headers_percent,
            "throughput_payload_percent": throughput_payload_percent,
        })

    if not rows:
        raise RuntimeError("Nenhum ficheiro UDP válido encontrado.")

    summary = {
        "run_name": "SUMMARY",
        "packets_sent": sum(r["packets_sent"] for r in rows),
        "packets_received": sum(r["packets_received"] for r in rows),
        "packets_lost": sum(r["packets_lost"] for r in rows),
        "loss_rate": (
            sum(r["packets_lost"] for r in rows) / sum(r["packets_sent"] for r in rows)
            if sum(r["packets_sent"] for r in rows) > 0 else 0.0
        ),
        "loss_percent": (
            sum(r["packets_lost"] for r in rows) / sum(r["packets_sent"] for r in rows) * 100.0
            if sum(r["packets_sent"] for r in rows) > 0 else 0.0
        ),
        "throughput_with_headers_mbps": mean(r["throughput_with_headers_mbps"] for r in rows),
        "throughput_payload_mbps": mean(r["throughput_payload_mbps"] for r in rows),
        "throughput_with_headers_percent": mean(r["throughput_with_headers_percent"] for r in rows),
        "throughput_payload_percent": mean(r["throughput_payload_percent"] for r in rows),
    }

    with output_file.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "run_name",
                "packets_sent",
                "packets_received",
                "packets_lost",
                "loss_rate",
                "loss_percent",
                "throughput_with_headers_mbps",
                "throughput_payload_mbps",
                "throughput_with_headers_percent",
                "throughput_payload_percent",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(summary)

    print(f"Resumo escrito em: {output_file}")


if __name__ == "__main__":
    main()
