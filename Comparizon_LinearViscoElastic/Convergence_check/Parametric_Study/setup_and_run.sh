#!/bin/bash
set -e

# ============================================================================
# SETUP AND RUN: Complete Fresh Parametric Study
# This script:
#   1. Removes all family directories (soft, stiff, initial) completely
#   2. Recreates them with proper structure
#   3. Runs the complete parametric study workflow
#
# Usage: ./setup_and_run.sh [family] [angle]
#   family: stiff, initial, soft, or all (default: all)
#   angle: 0, 10, or all (default: all)
#
# Always run from: Parametric_Study/
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_DIR="Parametric_Study"

# ============================================================================
# Check that we're running from Parametric_Study/
# ============================================================================
if [[ ! "$(basename "$SCRIPT_DIR")" == "$EXPECTED_DIR" ]]; then
    echo "❌ ERROR: This script must be run from the Parametric_Study/ directory!"
    echo ""
    echo "Current directory: $SCRIPT_DIR"
    echo "Expected directory name: $EXPECTED_DIR"
    echo ""
    echo "Please cd to Parametric_Study/ and try again:"
    echo "  cd Parametric_Study"
    echo "  ./setup_and_run.sh"
    exit 1
fi

cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     FRESH START: PARAMETRIC STUDY SETUP                     ║"
echo "║     Complete cleanup and workflow execution                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Working directory: $SCRIPT_DIR"
echo ""

# ============================================================================
# STEP 1: Complete Cleanup - Remove All Family Directories
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 1/3: Removing all family directories"
echo "════════════════════════════════════════════════════════════════"
echo ""

FAMILIES=(soft stiff initial)

for FAMILY in "${FAMILIES[@]}"; do
    if [ -d "$FAMILY" ]; then
        echo "  Removing: $FAMILY/"
        rm -rf "$FAMILY"
        echo "    ✓ Deleted"
    else
        echo "  $FAMILY/ - not present (OK)"
    fi
done

echo ""
echo "✅ All family directories removed"
echo ""

# ============================================================================
# STEP 2: Recreate Family Directories with Proper Structure
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 2/3: Creating fresh family directories"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Read available angles from config
CONFIG_FILE="${SCRIPT_DIR}/mesh_generation/config_parametric_study.py"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    exit 1
fi

# Extract ANGLES from Python config file
ANGLES=($(python3 -c "import sys; sys.path.insert(0, '${SCRIPT_DIR}/mesh_generation'); from config_parametric_study import ANGLES; print(' '.join(map(str, ANGLES)))"))

echo "Creating structure for angles: ${ANGLES[@]}"
echo ""

for FAMILY in "${FAMILIES[@]}"; do
    echo "  Creating: $FAMILY/"
    mkdir -p "$FAMILY"
    
    for ANGLE in "${ANGLES[@]}"; do
        # Create angle subdirectories with working directories
        mkdir -p "${FAMILY}/angle_${ANGLE}/Interface_models"
        mkdir -p "${FAMILY}/angle_${ANGLE}/Full_layer_models"
        mkdir -p "${FAMILY}/angle_${ANGLE}/comparison_results"
        
        echo "    ✓ ${FAMILY}/angle_${ANGLE}/ (Interface_models, Full_layer_models, comparison_results)"
    done
    
    # Create __pycache__ to prevent Python from cluttering
    mkdir -p "${FAMILY}/__pycache__"
done

echo ""
echo "✅ Fresh family directories created with proper structure"
echo ""

# Verify structure
echo "Directory structure verification:"
for FAMILY in "${FAMILIES[@]}"; do
    ANGLE_COUNT=$(ls -d ${FAMILY}/angle_* 2>/dev/null | wc -l)
    echo "  $FAMILY: $ANGLE_COUNT angle directories"
done
echo ""

# ============================================================================
# STEP 3: Run Complete Workflow
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 3/3: Running complete parametric study workflow"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Parse arguments (passed to workflow script)
REQUESTED_FAMILY="${1:-all}"
REQUESTED_ANGLE="${2:-all}"

echo "Workflow configuration:"
echo "  Families: $REQUESTED_FAMILY"
echo "  Angles: $REQUESTED_ANGLE"
echo ""

# Run the master workflow
LOG_FILE="parametric_study_run_$(date +%Y%m%d_%H%M%S).log"
echo "Starting workflow... (logging to $LOG_FILE)"
echo ""

./run_workflow.sh "$REQUESTED_FAMILY" "$REQUESTED_ANGLE" 2>&1 | tee "$LOG_FILE"

WORKFLOW_EXIT=$?

echo ""
if [ $WORKFLOW_EXIT -eq 0 ]; then
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     PARAMETRIC STUDY COMPLETED SUCCESSFULLY!                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Results locations:"
    echo "  Individual convergence:"
    for FAMILY in "${FAMILIES[@]}"; do
        for ANGLE in "${ANGLES[@]}"; do
            if [ -d "${FAMILY}/angle_${ANGLE}/comparison_results" ]; then
                PKL_COUNT=$(ls ${FAMILY}/angle_${ANGLE}/comparison_results/*.pkl 2>/dev/null | wc -l)
                echo "    ${FAMILY}/angle_${ANGLE}/comparison_results/ ($PKL_COUNT .pkl files)"
            fi
        done
    done
    echo ""
    echo "  Cross-family plots:"
    if [ -d "comparison_plots" ]; then
        for ANGLE in "${ANGLES[@]}"; do
            if [ -d "comparison_plots/angle_${ANGLE}" ]; then
                PLOT_COUNT=$(find comparison_plots/angle_${ANGLE} -name "*.png" 2>/dev/null | wc -l)
                echo "    comparison_plots/angle_${ANGLE}/ ($PLOT_COUNT plots)"
            fi
        done
    fi
    echo ""
    echo "Log file: $LOG_FILE"
else
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     WORKFLOW FAILED!                                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Check the log file for details: $LOG_FILE"
    exit $WORKFLOW_EXIT
fi
