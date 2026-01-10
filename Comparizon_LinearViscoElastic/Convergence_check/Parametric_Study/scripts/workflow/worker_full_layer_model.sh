#!/bin/bash

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
FAMILY=$1
ANGLE=$2
m=$3
n=$4
E_M=$5
E_I=$6
E_0=$7
BASE_DIR=$8
nKelvin=${9}
minTau=${10}
timeToDays=${11}
MaterialID=${12}
shift 12
HEIGHTS=("$@")  # Remaining arguments are heights

PARAM_M_LABEL="${m}"
PARAM_N_LABEL="${n}"
WORK_DIR_BASE="${BASE_DIR}/${FAMILY}/angle_${ANGLE}/m_${PARAM_M_LABEL}/n_${PARAM_N_LABEL}"
OUT_DIR="${BASE_DIR}/RESULTS/${FAMILY}/angle_${ANGLE}"
WORK_DIR="${WORK_DIR_BASE}/Full_layer_models"
SOLVER_LOG_DIR="${WORK_DIR_BASE}/solver_logs"

echo "[$(date '+%H:%M:%S')] Starting: $FAMILY / angle_${ANGLE} /m_${PARAM_M_LABEL}/n_${PARAM_N_LABEL}"

# Create directories
mkdir -p "${WORK_DIR}/cases"
mkdir -p "${WORK_DIR}/force_displacement_results"
mkdir -p "$SOLVER_LOG_DIR"
mkdir -p "$OUT_DIR"

TEMPLATE_DIR="${BASE_DIR}/mesh_generation/Full_layer_models"
MESH_DATA_DIR="${BASE_DIR}/mesh_generation/Full_layer_models/angle_${ANGLE}"

# Main loop over heights
for h in "${HEIGHTS[@]}"; do
    TEMPLATE="${TEMPLATE_DIR}/LinearViscoElastic_Full_Cauchy_Template_three_body_model_angle_${ANGLE}_h_${h}.inp"
    JOB_FILE="${WORK_DIR}/Full_layer_${ANGLE}_h_${h}_m_${m}_n_${n}_job.inp"

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
    # Run postprocessing (stay in FULL_DIR where .case files are)
    echo "  Running postprocessing..."
    cat > "tmp_postprocess_${h}.py" << 'PYCODE'
import sys, os, traceback
from pathlib import Path
sys.path.insert(0, "%(eval_scripts_path)s")
from Full_Model_Evaluate_traction_jump import compute_and_save_traction_jump
from Full_Model_Evaluate_displacement_jump import compute_and_save_displacement_jump

case_bottom = Path("Cauchy_Full_model_bottom_%(h)s.case")
case_top = Path("Cauchy_Full_model_top_%(h)s.case")
layer_h = float("%(h)s")
angle_deg = float("%(angle)d")
m = float("%(m)s")
n = float("%(n)s")
out_dir = Path("cases")
out_dir.mkdir(exist_ok=True)
try:
    compute_and_save_traction_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        m = m,
        n = n,
        output_dir=str(out_dir),
        plot=False
    )
    compute_and_save_displacement_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        m = m,
        n = n,
        output_dir=str(out_dir),
        plot=False
    )
    print(f"✓ Postprocessing complete: cases/Full_h_{layer_h}_angle_{angle_deg}_m_{m}_n_{n}.pkl files created")
except Exception:
    traceback.print_exc(); sys.exit(2)
PYCODE
    
    # Substitute variables (evaluation_scripts in centralized directory)
    sed -i "s|%(eval_scripts_path)s|${BASE_DIR}/evaluation_scripts|g; s|%(h)s|${h}|g; s|%(angle)d|${ANGLE}|g; s|%(m)s|${m}|g; s|%(n)s|${n}|g" "tmp_postprocess_${h}.py"
    
    if ! mamba run -n alexandros_Plot pvpython "tmp_postprocess_${h}.py" > "postprocess_${h}.log" 2>&1; then
        echo "❌ Postprocessing failed for h=$h"
        cat "postprocess_${h}.log"
        exit 1
    fi
    
rm -f "tmp_postprocess_${h}.py"
cd "${BASE_DIR}"
echo "✓ h=$h complete"
echo ""
echo "[$(date '+%H:%M:%S')] ✓ Completed: $FAMILY / angle_${ANGLE} /m_${PARAM_M_LABEL}/n_${PARAM_N_LABEL}"
echo "✅ Full Layer reference model (h=$FULL_HEIGHT) completed"
echo ""
done