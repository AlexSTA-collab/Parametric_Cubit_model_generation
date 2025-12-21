#!/bin/bash

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
FAMILY=$1
ANGLE=$2
m=$3
M_LABEL=$4
n=$5
E_M=$6
E_I=$7
E_0=$8
BASE_DIR=$9
nKelvin=${10}
minTau=${11}
timeToDays=${12}
MaterialID=${13}
shift 13
HEIGHTS=("$@")  # Remaining arguments are heights

PARAM_M_LABEL="m_${m}"
PARAM_N_LABEL="n_${n}"
WORK_DIR_BASE="${BASE_DIR}/${FAMILY}/angle_${ANGLE}/m_${PARAM_M_LABEL}/n_${PARAM_N_LABEL}"
OUT_DIR="${BASE_DIR}/RESULTS/${FAMILY}/angle_${ANGLE}"
WORK_DIR="${WORK_DIR_BASE}/Interface_models"
SOLVER_LOG_DIR="${WORK_DIR_BASE}/solver_logs"

echo "[$(date '+%H:%M:%S')] Starting: $FAMILY / angle_${ANGLE} /m_${PARAM_M_LABEL}/n_${PARAM_N_LABEL}"

# Create directories
mkdir -p "${WORK_DIR}/cases"
mkdir -p "${WORK_DIR}/force_displacement_results"
mkdir -p "$SOLVER_LOG_DIR"
mkdir -p "$OUT_DIR"

TEMPLATE_DIR="${BASE_DIR}/mesh_generation/Interface_models"
MESH_DATA_DIR="${BASE_DIR}/mesh_generation/Interface_models/angle_${ANGLE}"

# Main loop over heights
for h in "${HEIGHTS[@]}"; do
    TEMPLATE="${TEMPLATE_DIR}/LinearViscoElastic_Interface_Template_three_body_model_angle_${ANGLE}_h_${h}.inp"
    JOB_FILE="${WORK_DIR}/Interface_${ANGLE}_h_${h}_m_${m}_n_${n}_job.inp"

    if [ ! -f "$TEMPLATE" ]; then
        echo "  ❌ Template not found: $TEMPLATE"
        exit 1
    fi

    # Generate job file - export all variables for template substitution
    export h E_M E_I E_0 m n nKelvin minTau timeToDays MaterialID
    export MESH_DATA_PATH="${MESH_DATA_DIR}/height_${h}"

    envsubst '${E_M} ${E_I} ${E_0} ${h} ${m} ${n} ${nKelvin} ${minTau} ${timeToDays} ${MaterialID}' < "$TEMPLATE" | \
        sed "s|height_${h}/|${MESH_DATA_PATH}/|g" > "$JOB_FILE"

    # Run solver
    cd "${WORK_DIR}"
    if ! mamba run -n alexandros edelweissfe "$(basename $JOB_FILE)" > "$SOLVER_LOG_DIR/solver_h_${h}_m_${m}_n_${n}.log" 2>&1; then
        echo "  ❌ Solver failed for h=$h"
        exit 1
    fi

    # ParaView extraction
    PARA_EXTRACTION_ARGS=("${WORK_DIR}" "${OUT_DIR}" "$E_M" "$E_I" "$E_0" "$h" "$m" "$n" "$FAMILY" "$ANGLE")
    bash "${BASE_DIR}/evaluate_force_displacement_scripts/run_paraview_extraction.sh" "${PARA_EXTRACTION_ARGS[@]}" > "${WORK_DIR}/paraview_h_${h}_m_${m}_n_${n}.log" 2>&1 || true
    cd "${BASE_DIR}"
done

echo "[$(date '+%H:%M:%S')] ✓ Completed: $FAMILY / angle_${ANGLE} /m_${PARAM_M_LABEL}/n_${PARAM_N_LABEL}"
