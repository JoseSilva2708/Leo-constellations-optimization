#!/bin/bash
set -euo pipefail

source thesis_environment/bin/activate

export PYTHONPATH="/home/admin/Tese/hypatia:${PYTHONPATH:-}"

ROOT_DIR="/home/admin/Tese"
INPUT_FILE="$ROOT_DIR/individuos.txt"


OUTPUT_ROOT="$ROOT_DIR/results"
SATNET_DIR="$ROOT_DIR/hypatia/paper/satellite_networks_state"
ANALYSIS_DIR="$ROOT_DIR/hypatia/paper/satgenpy_analysis"
NS3_DIR="$ROOT_DIR/hypatia/paper/ns3_experiments/scenario"
EVO_ALG_DIR="$ROOT_DIR/files_thesis/Evo_alg"

PY_EVO_ALG="$EVO_ALG_DIR/main.py"
PY_WALKER="$SATNET_DIR/main_my_walker.py"
PY_ANALYSIS="$ANALYSIS_DIR/my_analysis.py"
PY_RTT="$ANALYSIS_DIR/calculate_media_rtts_2.py"
PY_NS3_GENERATE_RUNS="$NS3_DIR/step_1_generate_runs.py"
PY_NS3_RUN="$NS3_DIR/step_2_run.py"
PY_PING_SUMMARY="$NS3_DIR/step_5_sintetize_ping_metrics.py"
PY_UDP_SUMMARY="$NS3_DIR/step_4_sintetize_metrics.py"
PY_PING_TIMESERIES="$NS3_DIR/step_6_pings_over_time.py"

pushd "$EVO_ALG_DIR" > /dev/null
python -u "$PY_EVO_ALG"
popd > /dev/null


if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Erro: ficheiro não encontrado: $INPUT_FILE"
    exit 1
fi


INDIVIDUO_ID=1

while IFS=',' read -r S P F inc h; do
    [[ -z "${S// }" ]] && continue

    INDIVIDUO_ID=$((INDIVIDUO_ID + 1))
    NUM_SATS=$((S * P))

    echo "========================================"
    echo "A processar individuo_${INDIVIDUO_ID}"
    echo "S=$S P=$P F=$F inc=$inc h=$h"
    echo "NUM_SATS=$NUM_SATS"
    echo "========================================"

    # 1) Gerar constelação
    pushd "$SATNET_DIR" > /dev/null
    python "$PY_WALKER" \
        --num-orbs "$S" \
        --num-sats-per-orb "$P" \
        --phase "$F" \
        --inclination "$inc" \
        --altitude-m "$h"
    popd > /dev/null

    # 2) Correr análise satgenpy
    pushd "$ANALYSIS_DIR" > /dev/null
    python "$PY_ANALYSIS" --num-sats "$NUM_SATS"
    popd > /dev/null

    # 3) Calcular média RTT
    python "$PY_RTT" \
        --num-sats "$NUM_SATS" \
        --individuo-id "$INDIVIDUO_ID" \
        --output-root "$OUTPUT_ROOT"

    # 4) Simular via ns3 e gerar valores sintetizados para análise
    pushd "$NS3_DIR" > /dev/null
    python "$PY_NS3_GENERATE_RUNS" --num-sats "$NUM_SATS"

    python "$PY_NS3_RUN" --num-sats "$NUM_SATS"

    python "$PY_UDP_SUMMARY" \
    --runs-dir "$NS3_DIR/runs" \
    --individuo-id "$INDIVIDUO_ID" \
    --output-root "$OUTPUT_ROOT"

    python "$PY_PING_SUMMARY" \
    --runs-dir "$NS3_DIR/runs" \
    --individuo-id "$INDIVIDUO_ID" \
    --output-root "$OUTPUT_ROOT"

    python "$PY_PING_TIMESERIES" \
    --runs-dir "$NS3_DIR/runs" \
    --individuo-id "$INDIVIDUO_ID" \
    --output-root "$OUTPUT_ROOT" \
    --relative-start
    popd > /dev/null

done < <(tail -n +2 "$INPUT_FILE")