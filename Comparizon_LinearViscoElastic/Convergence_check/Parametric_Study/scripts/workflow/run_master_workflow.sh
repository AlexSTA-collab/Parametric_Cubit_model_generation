#!/bin/bash
set -e

# ============================================================================
# MASTER WORKFLOW: Run parametric study for material families
# Usage: ./run_master_workflow.sh [family] [angle]
#   family: stiff, initial, soft, or all (default: all families)
#   angle: 0, 10, or all (default: read from config, or all if not specified)
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$BASE_DIR"

# Parse command line arguments
REQUESTED_FAMILY="${1:-all}"
REQUESTED_ANGLE="${2:-all}"

# Define families and their parameters
declare -A FAMILY_PARAMS
FAMILY_PARAMS[stiff]="E_M=2e5 E_I=4e3 E_0=4e5"
FAMILY_PARAMS[initial]="E_M=2e5 E_I=4e3 E_0=4e3"
FAMILY_PARAMS[soft]="E_M=2e5 E_I=4e3 E_0=4e-5"

# Determine which families to process
if [[ "$REQUESTED_FAMILY" == "all" ]]; then
    FAMILIES=(stiff initial soft)
else
    FAMILIES=($REQUESTED_FAMILY)
fi

# Read angles from centralized config file
CONFIG_FILE="${BASE_DIR}/mesh_generation/config_parametric_study.py"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    exit 1
fi

# Extract ANGLES from Python config file
AVAILABLE_ANGLES=($(python3 -c "import sys; sys.path.insert(0, '${BASE_DIR}/mesh_generation'); from config_parametric_study import ANGLES; print(' '.join(map(str, ANGLES)))"))

# Determine which angles to process
if [[ "$REQUESTED_ANGLE" == "all" ]]; then
    ANGLES=("${AVAILABLE_ANGLES[@]}")
else
    ANGLES=($REQUESTED_ANGLE)
fi

HEIGHTS=(0.01 0.02 0.04 0.06 0.08 0.1)
FULL_HEIGHT=0.01  # Only run Full Cauchy for this height

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         MASTER WORKFLOW: PARAMETRIC STUDY                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Available angles from config: ${AVAILABLE_ANGLES[@]}"
echo "  Angles to process: ${ANGLES[@]}"
echo "  Families to process: ${FAMILIES[@]}"
echo "  Heights: ${HEIGHTS[@]}"
echo ""

# ============================================================================
# Process each angle and family combination
# ============================================================================
for ANGLE in "${ANGLES[@]}"; do
for FAMILY in "${FAMILIES[@]}"; do

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         PROCESSING FAMILY: $FAMILY"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Ensure family directory structure exists (create if needed)
if [ ! -d "${FAMILY}" ]; then
    echo "⚠️  Creating ${FAMILY}/ directory structure..."
    mkdir -p "${FAMILY}/angle_${ANGLE}/Interface_models"
    mkdir -p "${FAMILY}/angle_${ANGLE}/Full_layer_models"
    mkdir -p "${FAMILY}/angle_${ANGLE}/comparison_results"
    mkdir -p "${FAMILY}/__pycache__"
    echo "✓ Directory structure created"
elif [ ! -d "${FAMILY}/angle_${ANGLE}" ]; then
    echo "⚠️  Creating ${FAMILY}/angle_${ANGLE}/ subdirectories..."
    mkdir -p "${FAMILY}/angle_${ANGLE}/Interface_models"
    mkdir -p "${FAMILY}/angle_${ANGLE}/Full_layer_models"
    mkdir -p "${FAMILY}/angle_${ANGLE}/comparison_results"
    echo "✓ Angle subdirectories created"
fi

# Set parameters for this family
PARAMS="${FAMILY_PARAMS[$FAMILY]}"
export E_M=$(echo $PARAMS | grep -oP 'E_M=\K[^ ]+')
export E_I=$(echo $PARAMS | grep -oP 'E_I=\K[^ ]+')
export E_0=$(echo $PARAMS | grep -oP 'E_0=\K[^ ]+')

echo "Parameters: E_M=$E_M, E_I=$E_I, E_0=$E_0"
echo "Family: $FAMILY"
echo ""

# ============================================================================
# STEP 1: Run Interface Models
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 1: Running Interface Models"
echo "════════════════════════════════════════════════════════════════"

# Centralized template location
TEMPLATE_DIR="${BASE_DIR}/mesh_generation/Interface_models"
MESH_DATA_DIR="${BASE_DIR}/mesh_generation/Interface_models/angle_${ANGLE}"

# Family-specific working directory
WORK_DIR="${FAMILY}/angle_${ANGLE}/Interface_models"

# Clean previous outputs and create working directory
rm -rf ${WORK_DIR} 2>/dev/null || true
mkdir -p ${WORK_DIR}/cases

for h in "${HEIGHTS[@]}"; do
    echo ""
    echo "──────────────────────────────────────────────────────────────"
    echo "  Processing Interface h = $h"
    echo "──────────────────────────────────────────────────────────────"
    
    TEMPLATE="${TEMPLATE_DIR}/LinearElastic_Interface_Template_three_body_model_angle_${ANGLE}_h_${h}.inp"
    JOB_FILE="${WORK_DIR}/LinearElastic_Interface_three_body_model_angle_${ANGLE}_h_${h}_job.inp"
    
    if [ ! -f "$TEMPLATE" ]; then
        echo "❌ Template not found: $TEMPLATE"
        exit 1
    fi
    
    # Generate job file with material parameters AND updated paths to centralized mesh data
    export h
    export MESH_DATA_PATH="${MESH_DATA_DIR}/height_${h}"
    
    # Replace material parameters and update include paths to absolute paths
    envsubst '${E_M} ${E_I} ${E_0} ${h}' < "$TEMPLATE" | \
        sed "s|height_${h}/|${MESH_DATA_PATH}/|g" > "$JOB_FILE"
    
    echo "✓ Generated: $JOB_FILE (references mesh data in ${MESH_DATA_PATH})"
    
    # Run solver (in WORK_DIR)
    echo "  Running solver..."
    cd "${BASE_DIR}/${WORK_DIR}"
    if ! mamba run -n alexandros edelweissfe "$(basename $JOB_FILE)" > "solver_${h}.log" 2>&1; then
        echo "❌ Solver failed for h=$h"
        cat "solver_${h}.log"
        exit 1
    fi
    
    # Check for .case files
    CASE_COUNT=$(ls -1 Cohesive_zone_model_*_${h}.case 2>/dev/null | wc -l)
    if [ "$CASE_COUNT" -ne 3 ]; then
        echo "❌ Expected 3 .case files, found $CASE_COUNT"
        exit 1
    fi
    echo "✓ Solver completed: 3 .case files created"
    
    # Run postprocessing (stay in INTERFACE_DIR where .case files are)
    echo "  Running postprocessing..."
    cat > "tmp_postprocess_${h}.py" << 'PYCODE'

import sys, os, traceback
from pathlib import Path
sys.path.insert(0, "%(eval_scripts_path)s")
from Interface_Model_Evaluate_traction_jump import compute_and_save_traction_jump
from Interface_Model_Evaluate_displacement_jump import compute_and_save_displacement_jump

case_bottom = Path("Cohesive_zone_model_bottom_%(h)s.case")
case_top = Path("Cohesive_zone_model_top_%(h)s.case")
layer_h = float("%(h)s")
angle_deg = float("%(angle)d")
out_dir = Path("cases")
out_dir.mkdir(exist_ok=True)
try:
    compute_and_save_traction_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        output_dir=str(out_dir),
        plot=False
    )
    compute_and_save_displacement_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        output_dir=str(out_dir),
        plot=False
    )
    print(f"✓ Postprocessing complete: cases/Interface_h_{layer_h}_angle_{angle_deg}.pkl files created")
except Exception:
    traceback.print_exc(); sys.exit(2)
PYCODE
    
    # Substitute variables (evaluation_scripts in centralized directory)
    sed -i "s|%(eval_scripts_path)s|${BASE_DIR}/evaluation_scripts|g; s|%(h)s|${h}|g; s|%(angle)d|${ANGLE}|g" "tmp_postprocess_${h}.py"
    
    if ! mamba run -n alexandros_Plot pvpython "tmp_postprocess_${h}.py" > "postprocess_${h}.log" 2>&1; then
        echo "❌ Postprocessing failed for h=$h"
        cat "postprocess_${h}.log"
        exit 1
    fi
    
    rm -f "tmp_postprocess_${h}.py"
    cd "${BASE_DIR}"
    echo "✓ h=$h complete"
done

echo ""
echo "✅ All Interface models completed"
echo ""

# ============================================================================
# STEP 2: Run Full Layer Models  
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 2: Running Full Layer Models"
echo "════════════════════════════════════════════════════════════════"

# Centralized template location
FULL_TEMPLATE_DIR="${BASE_DIR}/mesh_generation/Full_layer_models"
FULL_MESH_DATA_DIR="${BASE_DIR}/mesh_generation/Full_layer_models/angle_${ANGLE}"

# Family-specific working directory
FULL_WORK_DIR="${FAMILY}/angle_${ANGLE}/Full_layer_models"

# Clean previous outputs and create working directory
rm -rf ${FULL_WORK_DIR} 2>/dev/null || true
mkdir -p ${FULL_WORK_DIR}/cases

# Only run Full Cauchy for h=0.01
h=$FULL_HEIGHT
echo ""
echo "──────────────────────────────────────────────────────────────"
echo "  Processing Full Layer h = $h (REFERENCE)"
echo "──────────────────────────────────────────────────────────────"
    
    TEMPLATE="${FULL_TEMPLATE_DIR}/LinearElastic_Full_Cauchy_Template_three_body_model_angle_${ANGLE}_h_${h}.inp"
    JOB_FILE="${FULL_WORK_DIR}/LinearElastic_Full_Cauchy_three_body_model_angle_${ANGLE}_h_${h}_job.inp"
    
    if [ ! -f "$TEMPLATE" ]; then
        echo "❌ Template not found: $TEMPLATE"
        exit 1
    fi
    
    # Generate job file with material parameters AND updated paths to centralized mesh data
    export h
    export FULL_MESH_DATA_PATH="${FULL_MESH_DATA_DIR}/height_${h}"
    
    # Replace material parameters and update include paths to absolute paths
    envsubst '${E_M} ${E_I} ${E_0} ${h}' < "$TEMPLATE" | \
        sed "s|height_${h}/|${FULL_MESH_DATA_PATH}/|g" > "$JOB_FILE"
    
    echo "✓ Generated: $JOB_FILE (references mesh data in ${FULL_MESH_DATA_PATH})"
    
    # Run solver (in FULL_WORK_DIR)
    echo "  Running solver..."
    cd "${BASE_DIR}/${FULL_WORK_DIR}"
    if ! mamba run -n alexandros edelweissfe "$(basename $JOB_FILE)" > "solver_${h}.log" 2>&1; then
        echo "❌ Solver failed for h=$h"
        cat "solver_${h}.log"
        exit 1
    fi
    
    # Check for .case files
    CASE_COUNT=$(ls -1 Cauchy_Full_model_*_${h}.case 2>/dev/null | wc -l)
    if [ "$CASE_COUNT" -ne 3 ]; then
        echo "❌ Expected 3 .case files, found $CASE_COUNT"
        exit 1
    fi
    echo "✓ Solver completed: 3 .case files created"
    
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
out_dir = Path("cases")
out_dir.mkdir(exist_ok=True)
try:
    compute_and_save_traction_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        output_dir=str(out_dir),
        plot=False
    )
    compute_and_save_displacement_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        output_dir=str(out_dir),
        plot=False
    )
    print(f"✓ Postprocessing complete: cases/Full_h_{layer_h}_angle_{angle_deg}.pkl files created")
except Exception:
    traceback.print_exc(); sys.exit(2)
PYCODE
    
    # Substitute variables (evaluation_scripts in centralized directory)
    sed -i "s|%(eval_scripts_path)s|${BASE_DIR}/evaluation_scripts|g; s|%(h)s|${h}|g; s|%(angle)d|${ANGLE}|g" "tmp_postprocess_${h}.py"
    
    if ! mamba run -n alexandros_Plot pvpython "tmp_postprocess_${h}.py" > "postprocess_${h}.log" 2>&1; then
        echo "❌ Postprocessing failed for h=$h"
        cat "postprocess_${h}.log"
        exit 1
    fi
    
rm -f "tmp_postprocess_${h}.py"
cd "${BASE_DIR}"
echo "✓ h=$h complete"

echo ""
echo "✅ Full Layer reference model (h=$FULL_HEIGHT) completed"
echo ""

# ============================================================================
# STEP 3: Run Convergence Analysis
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 3: Running Convergence Analysis for $FAMILY"
echo "════════════════════════════════════════════════════════════════"

# Use the parametrized convergence analysis script
# Located in scripts/postprocessing/
python3 "${BASE_DIR}/scripts/postprocessing/convergence_analysis.py" "$FAMILY" "$ANGLE" "L1"

if [ $? -eq 0 ]; then
    echo "✅ Convergence analysis completed for $FAMILY"
    echo ""
    echo "Results location:"
    echo "  ${FAMILY}/angle_${ANGLE}/comparison_results/"
else
    echo "❌ Convergence analysis failed for $FAMILY"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   FAMILY $FAMILY, ANGLE $ANGLE COMPLETED SUCCESSFULLY         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

done  # End of family loop
done  # End of angle loop

# ============================================================================
# STEP 4: Generate Cross-Family Comparative Plots
# ============================================================================
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "STEP 4: Generating Cross-Family Comparative Plots"
echo "════════════════════════════════════════════════════════════════"
echo ""

cd "${BASE_DIR}"

if ! python3 scripts/postprocessing/master_parametric_script.py > master_parametric_plots.log 2>&1; then
    echo "❌ Cross-family plot generation failed"
    cat master_parametric_plots.log
    exit 1
fi

echo "✅ Cross-family comparative plots generated"
echo ""

# ============================================================================
# Final Summary
# ============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                ALL WORKFLOWS COMPLETED SUCCESSFULLY          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Processed angles: ${ANGLES[@]}"
echo "Processed families: ${FAMILIES[@]}"
echo ""
echo "Results locations:"
echo "  Individual convergence plots:"
for ANGLE in "${ANGLES[@]}"; do
    for FAMILY in "${FAMILIES[@]}"; do
        echo "    - ${FAMILY}/angle_${ANGLE}/comparison_results/"
    done
done
echo ""
echo "  Cross-family comparative plots:"
for ANGLE in "${ANGLES[@]}"; do
    echo "    - comparison_plots/angle_${ANGLE}/"
done
echo ""
echo "✅ Complete parametric study finished successfully!"
