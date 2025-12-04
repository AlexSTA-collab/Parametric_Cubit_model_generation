#!/bin/bash
set -e

# ============================================================================
# MASTER WORKFLOW: Run parametric study for material families
# Usage: ./run_master_workflow.sh [family]
#   family: stiff, initial, or soft (default: all families)
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse command line argument
REQUESTED_FAMILY="${1:-all}"

# Define families and their parameters
declare -A FAMILY_PARAMS
FAMILY_PARAMS[stiff]="E_M=2e5 E_I=4e3 E_0=4e7"
FAMILY_PARAMS[initial]="E_M=2e5 E_I=4e3 E_0=4e5"
FAMILY_PARAMS[soft]="E_M=2e5 E_I=4e3 E_0=4e-5"

# Determine which families to process
if [[ "$REQUESTED_FAMILY" == "all" ]]; then
    FAMILIES=(stiff initial soft)
else
    FAMILIES=($REQUESTED_FAMILY)
fi

ANGLE=10
HEIGHTS=(0.01 0.02 0.04 0.06 0.08 0.1)
FULL_HEIGHT=0.01  # Only run Full Cauchy for this height

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         MASTER WORKFLOW: PARAMETRIC STUDY                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Families to process: ${FAMILIES[@]}"
echo "Heights: ${HEIGHTS[@]}"
echo ""

# ============================================================================
# Process each family
# ============================================================================
for FAMILY in "${FAMILIES[@]}"; do

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         PROCESSING FAMILY: $FAMILY"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

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

INTERFACE_DIR="${FAMILY}/angle_${ANGLE}/Interface_models_templates"

# Clean previous outputs
rm -f ${INTERFACE_DIR}/*.case ${INTERFACE_DIR}/*.ensight* ${INTERFACE_DIR}/*_job.inp ${INTERFACE_DIR}/Cohesive_* ${INTERFACE_DIR}/cases/*.pkl 2>/dev/null || true
mkdir -p ${INTERFACE_DIR}/cases

for h in "${HEIGHTS[@]}"; do
    echo ""
    echo "──────────────────────────────────────────────────────────────"
    echo "  Processing Interface h = $h"
    echo "──────────────────────────────────────────────────────────────"
    
    TEMPLATE="${INTERFACE_DIR}/LinearElastic_Interface_Template_three_body_model_angle_${ANGLE}_h_${h}.inp"
    JOB_FILE="${INTERFACE_DIR}/LinearElastic_Interface_three_body_model_angle_${ANGLE}_h_${h}_job.inp"
    
    if [ ! -f "$TEMPLATE" ]; then
        echo "❌ Template not found: $TEMPLATE"
        exit 1
    fi
    
    # Generate job file with envsubst
    export h
    envsubst '${E_M} ${E_I} ${E_0} ${h}' < "$TEMPLATE" > "$JOB_FILE"
    echo "✓ Generated: $JOB_FILE"
    
    # Run solver (in INTERFACE_DIR)
    echo "  Running solver..."
    cd "${SCRIPT_DIR}/${INTERFACE_DIR}"
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
    
    # Substitute variables
    sed -i "s|%(eval_scripts_path)s|${SCRIPT_DIR}/evaluation_scripts|g; s|%(h)s|${h}|g; s|%(angle)d|${ANGLE}|g" "tmp_postprocess_${h}.py"
    
    if ! mamba run -n alexandros_Plot pvpython "tmp_postprocess_${h}.py" > "postprocess_${h}.log" 2>&1; then
        echo "❌ Postprocessing failed for h=$h"
        cat "postprocess_${h}.log"
        exit 1
    fi
    
    rm -f "tmp_postprocess_${h}.py"
    cd "${SCRIPT_DIR}"
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

FULL_DIR="${FAMILY}/angle_${ANGLE}/Full_layer_models_templates"

# Clean previous outputs
rm -f ${FULL_DIR}/*.case ${FULL_DIR}/*.ensight* ${FULL_DIR}/*_job.inp ${FULL_DIR}/Cauchy_* ${FULL_DIR}/cases/*.pkl 2>/dev/null || true
mkdir -p ${FULL_DIR}/cases

# Only run Full Cauchy for h=0.01
h=$FULL_HEIGHT
echo ""
echo "──────────────────────────────────────────────────────────────"
echo "  Processing Full Layer h = $h (REFERENCE)"
echo "──────────────────────────────────────────────────────────────"
    
    TEMPLATE="${FULL_DIR}/LinearElastic_Full_Cauchy_Template_three_body_model_angle_${ANGLE}_h_${h}.inp"
    JOB_FILE="${FULL_DIR}/LinearElastic_Full_Cauchy_three_body_model_angle_${ANGLE}_h_${h}_job.inp"
    
    if [ ! -f "$TEMPLATE" ]; then
        echo "❌ Template not found: $TEMPLATE"
        exit 1
    fi
    
    # Generate job file with envsubst
    export h
    envsubst '${E_M} ${E_I} ${E_0} ${h}' < "$TEMPLATE" > "$JOB_FILE"
    echo "✓ Generated: $JOB_FILE"
    
    # Run solver (in FULL_DIR)
    echo "  Running solver..."
    cd "${SCRIPT_DIR}/${FULL_DIR}"
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
    
    # Substitute variables
    sed -i "s|%(eval_scripts_path)s|${SCRIPT_DIR}/evaluation_scripts|g; s|%(h)s|${h}|g; s|%(angle)d|${ANGLE}|g" "tmp_postprocess_${h}.py"
    
    if ! mamba run -n alexandros_Plot pvpython "tmp_postprocess_${h}.py" > "postprocess_${h}.log" 2>&1; then
        echo "❌ Postprocessing failed for h=$h"
        cat "postprocess_${h}.log"
        exit 1
    fi
    
rm -f "tmp_postprocess_${h}.py"
cd "${SCRIPT_DIR}"
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

cd "$SCRIPT_DIR/${FAMILY}/angle_${ANGLE}"

# Run the convergence analysis script
python3 Final_comparizon_convergence_fixed_range_publication.py

if [ $? -eq 0 ]; then
    echo "✅ Convergence analysis completed for $FAMILY"
    echo ""
    echo "Results location:"
    echo "  ${FAMILY}/angle_${ANGLE}/comparison_results/"
else
    echo "❌ Convergence analysis failed for $FAMILY"
    exit 1
fi

cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         FAMILY $FAMILY COMPLETED SUCCESSFULLY                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

done  # End of family loop

# ============================================================================
# Final Summary
# ============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                ALL WORKFLOWS COMPLETED SUCCESSFULLY          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Processed families: ${FAMILIES[@]}"
echo ""
echo "Results locations:"
for FAMILY in "${FAMILIES[@]}"; do
    echo "  - ${FAMILY}/angle_${ANGLE}/comparison_results/"
done
echo ""
echo "Next steps:"
echo "  1. Check convergence plots in each family's comparison_results/"
echo "  2. Compare results across families"
echo "  3. Use for publication"
