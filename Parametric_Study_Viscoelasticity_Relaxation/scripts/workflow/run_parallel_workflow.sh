#!/bin/bash
set -e

# ============================================================================
# PARALLEL WORKFLOW: Run parametric study with GNU Parallel
# This script distributes analyses across multiple CPU cores
# 
# Usage: run_parallel_workflow.sh NUM_JOBS FAMILY ANGLE [M] [N] [HEIGHTS...]
# 
# Arguments:
#   NUM_JOBS  - Number of parallel jobs (default: 4)
#   FAMILY    - Material family or 'all' (default: all)
#   ANGLE     - Angle value or 'all' (default: all)
#   M         - M parameter or 'all' (default: all)
#   N         - N parameter or 'all' (default: all)
#   HEIGHTS   - Optional list of heights (default: all from config)
#               Example: 0.01 0.1
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$BASE_DIR"

# Configuration
NUM_JOBS="${1:-4}"  # Default: 4 parallel jobs
REQUESTED_FAMILY="${2:-all}"
REQUESTED_ANGLE="${3:-all}"
REQUESTED_M="${4:-all}"
REQUESTED_N="${5:-all}"
shift 5 2>/dev/null || true
REQUESTED_HEIGHTS=()
for h in "$@"; do
    if [[ "$h" != "--no-plots" ]]; then
        REQUESTED_HEIGHTS+=("$h")
    fi
done

# Check if GNU parallel is installed
if ! command -v parallel &> /dev/null; then
    echo "❌ GNU Parallel is not installed!"
    echo ""
    echo "Install it with:"
    echo "  Ubuntu/Debian: sudo apt-get install parallel"
    echo "  Fedora/RHEL:   sudo dnf install parallel"
    echo "  macOS:         brew install parallel"
    echo ""
    echo "Or use the serial workflow: ./run_viscoelastic_study.sh"
    exit 1
fi

CONFIG_FILE="${BASE_DIR}/mesh_generation/config_parametric_study.py"

# Extract configuration using Python
read -r -d '' PYTHON_EXTRACT << 'PYCODE' || true
import sys
sys.path.insert(0, '${BASE_DIR}/mesh_generation')
from config_parametric_study import MATERIAL_FAMILIES, ANGLES, HEIGHT_VALUES_INTERFACE, M_VALUES, N_VALUES

# Print angles
print("ANGLES:", " ".join(map(str, ANGLES)))
print("FAMILIES:", " ".join(MATERIAL_FAMILIES.keys()))
print("HEIGHTS:", " ".join(map(str, HEIGHT_VALUES_INTERFACE)))

# Print m and n values
print("M_ELASTIC:", M_VALUES["elastic_limit"])
print("M_VISCOELASTIC:", M_VALUES["viscoelastic"])
print("M_VISCOUS:", M_VALUES["viscous_limit"])
print("N_VALUES:", " ".join(map(str, N_VALUES)))

# Print family parameters and viscoelastic constants
for family, params in MATERIAL_FAMILIES.items():
    print(f"FAMILY_{family.upper()}_E_M:", params["E_M"])
    print(f"FAMILY_{family.upper()}_E_I:", params["E_I"])
    print(f"FAMILY_{family.upper()}_E_0:", params["E_0"])

visco_params = MATERIAL_FAMILIES[list(MATERIAL_FAMILIES.keys())[0]]["viscoelastic_params"][0]
print("NKELVIN:", visco_params["nKelvin"])
print("MINTAU:", visco_params["minTau"])
print("TIMETODAYS:", visco_params["timeToDays"])
print("MATERIALID:", visco_params["MaterialID"])
PYCODE

PYTHON_EXTRACT="${PYTHON_EXTRACT/\$\{BASE_DIR\}/${BASE_DIR}}"
CONFIG_OUTPUT=$(python3 <<< "$PYTHON_EXTRACT")

# Parse configuration
AVAILABLE_ANGLES=($(echo "$CONFIG_OUTPUT" | grep "^ANGLES:" | cut -d: -f2))
AVAILABLE_FAMILIES=($(echo "$CONFIG_OUTPUT" | grep "^FAMILIES:" | cut -d: -f2))
HEIGHTS=($(echo "$CONFIG_OUTPUT" | grep "^HEIGHTS:" | cut -d: -f2))
M_ELASTIC=$(echo "$CONFIG_OUTPUT" | grep "^M_ELASTIC:" | cut -d: -f2 | tr -d ' ')
M_VISCOELASTIC=$(echo "$CONFIG_OUTPUT" | grep "^M_VISCOELASTIC:" | cut -d: -f2 | tr -d ' ')
M_VISCOUS=$(echo "$CONFIG_OUTPUT" | grep "^M_VISCOUS:" | cut -d: -f2 | tr -d ' ')
N_VALUES_ARR=($(echo "$CONFIG_OUTPUT" | grep "^N_VALUES:" | cut -d: -f2))
NKELVIN=$(echo "$CONFIG_OUTPUT" | grep "^NKELVIN:" | cut -d: -f2 | tr -d ' ')
MINTAU=$(echo "$CONFIG_OUTPUT" | grep "^MINTAU:" | cut -d: -f2 | tr -d ' ')
TIMETODAYS=$(echo "$CONFIG_OUTPUT" | grep "^TIMETODAYS:" | cut -d: -f2 | tr -d ' ')
MATERIALID=$(echo "$CONFIG_OUTPUT" | grep "^MATERIALID:" | cut -d: -f2 | tr -d ' ')

# Filter based on arguments
if [[ "$REQUESTED_FAMILY" == "all" ]]; then
    FAMILIES=("${AVAILABLE_FAMILIES[@]}")
else
    FAMILIES=($REQUESTED_FAMILY)
fi

if [[ "$REQUESTED_ANGLE" == "all" ]]; then
    ANGLES=("${AVAILABLE_ANGLES[@]}")
else
    ANGLES=($REQUESTED_ANGLE)
fi

if [[ "$REQUESTED_M" == "all" ]]; then
    M_LABELS=(elastic_limit viscoelastic viscous_limit)
    M_VALUES_TO_PROCESS=($M_ELASTIC $M_VISCOELASTIC $M_VISCOUS)
else
    case "$REQUESTED_M" in
        elastic_limit) M_LABELS=(elastic_limit); M_VALUES_TO_PROCESS=($M_ELASTIC) ;;
        viscoelastic) M_LABELS=(viscoelastic); M_VALUES_TO_PROCESS=($M_VISCOELASTIC) ;;
        viscous_limit) M_LABELS=(viscous_limit); M_VALUES_TO_PROCESS=($M_VISCOUS) ;;
        *) echo "❌ Invalid m_value"; exit 1 ;;
    esac
fi

if [[ "$REQUESTED_N" == "all" ]]; then
    N_VALUES_TO_PROCESS=("${N_VALUES_ARR[@]}")
else
    N_VALUES_TO_PROCESS=("${N_VALUES_ARR[$REQUESTED_N]}")
fi

# Filter heights
if [[ ${#REQUESTED_HEIGHTS[@]} -gt 0 ]]; then
    HEIGHTS=("${REQUESTED_HEIGHTS[@]}")
    echo "Using custom heights: ${HEIGHTS[@]}"
else
    # Use all heights from config
    HEIGHTS=($(echo "$CONFIG_OUTPUT" | grep "^HEIGHTS:" | cut -d: -f2))
fi
HEIGHTS_CLEAN=()
for h in "${HEIGHTS[@]}"; do
    if [[ "$h" != "--no-plots" ]]; then
        HEIGHTS_CLEAN+=("$h")
    fi
done

# Calculate total jobs
TOTAL_JOBS=$((${#FAMILIES[@]} * ${#ANGLES[@]} * ${#M_VALUES_TO_PROCESS[@]} * ${#N_VALUES_TO_PROCESS[@]}))

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         PARALLEL VISCOELASTIC PARAMETRIC STUDY               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Parallel jobs: $NUM_JOBS"
echo "  Families: ${FAMILIES[@]}"
echo "  Angles: ${ANGLES[@]}"
echo "  m values: ${M_LABELS[@]}"
echo "  n values: ${N_VALUES_TO_PROCESS[@]}"
echo "  Heights per combo: ${#HEIGHTS[@]}"
echo ""
echo "Total parameter combinations: $TOTAL_JOBS"
echo "Total analyses (× heights): $((TOTAL_JOBS * ${#HEIGHTS[@]}))"
echo ""
echo "Estimated speedup: ${NUM_JOBS}× faster than serial"
echo ""

# Create job list file
JOBLIST="${BASE_DIR}/parallel_jobs.txt"
rm -f "$JOBLIST"

echo "Generating job list..."
for FAMILY in "${FAMILIES[@]}"; do
    # Get family-specific parameters
    E_M_VAR="FAMILY_${FAMILY^^}_E_M"
    E_I_VAR="FAMILY_${FAMILY^^}_E_I"
    E_0_VAR="FAMILY_${FAMILY^^}_E_0"
    E_M=$(echo "$CONFIG_OUTPUT" | grep "^${E_M_VAR}:" | cut -d: -f2 | tr -d ' ')
    E_I=$(echo "$CONFIG_OUTPUT" | grep "^${E_I_VAR}:" | cut -d: -f2 | tr -d ' ')
    E_0=$(echo "$CONFIG_OUTPUT" | grep "^${E_0_VAR}:" | cut -d: -f2 | tr -d ' ')
    
    for ANGLE in "${ANGLES[@]}"; do
        for m_idx in "${!M_VALUES_TO_PROCESS[@]}"; do
            m="${M_VALUES_TO_PROCESS[$m_idx]}"
            M_LABEL="${M_LABELS[$m_idx]}"
            
            for n in "${N_VALUES_TO_PROCESS[@]}"; do
                # Each line: FAMILY ANGLE m M_LABEL n E_M E_I E_0
                echo "$FAMILY $ANGLE $m $M_LABEL $n $E_M $E_I $E_0" >> "$JOBLIST"
            done
        done
    done
done

echo "✓ Generated $TOTAL_JOBS job specifications"
echo ""

timeToDays=${12}
echo "[$(date '+%H:%M:%S')] Starting: $FAMILY / angle_${ANGLE} /m_${PARAM_M_LABEL}/n_${PARAM_N_LABEL}"
echo "[$(date '+%H:%M:%S')] ✓ Completed: $FAMILY / angle_${ANGLE} / $PARAM_LABEL"
echo "Starting parallel execution with $NUM_JOBS jobs..."
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Progress will be shown below. Log files saved in each result directory."
echo ""


# Use GNU parallel with progress bar, calling the modular worker script
WORKER_SCRIPT="${SCRIPT_DIR}/worker_interface_model.sh"
chmod +x "$WORKER_SCRIPT"
HEIGHTS_CLEAN=()
for h in "${HEIGHTS[@]}"; do
    if [[ "$h" != "--no-plots" ]]; then
        HEIGHTS_CLEAN+=("$h")
    fi
done
parallel --progress --jobs "$NUM_JOBS" --colsep ' ' \
    "$WORKER_SCRIPT" {1} {2} {3} {4} {5} {6} {7} {8} "$BASE_DIR" "$NKELVIN" "$MINTAU" "$TIMETODAYS" "$MATERIALID" "${HEIGHTS_CLEAN[@]}" \
    :::: "$JOBLIST"

# Cleanup
rm -f "$JOBLIST"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          PARALLEL EXECUTION COMPLETED                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Processed $TOTAL_JOBS parameter combinations"
echo "Total analyses: $((TOTAL_JOBS * ${#HEIGHTS[@]}))"
echo ""
echo "Raw analysis location:"
echo "  {family}/angle_{X}/m_{Y}/n_{Z}/Interface_models/"
echo ""
echo "Aggregated results location:"
echo "  Results/{family}/angle_{X}/parametric_curves_creep.pkl"
echo ""
echo "✅ All analyses completed successfully!"

# ================================================================
# Generate final plots (ONE per family / angle)
# ================================================================
echo ""
echo "Generating final plots for each family/angle..."
echo "================================================"

for FAMILY in "${FAMILIES[@]}"; do
    for ANGLE in "${ANGLES[@]}"; do

        PKL_PATH="RESULTS/${FAMILY}/angle_${ANGLE}/parametric_curves_creep.pkl"
        OUTDIR="comparison_plots/${FAMILY}_angle_${ANGLE}"

        if [ -f "$PKL_PATH" ]; then
            echo "  → Plotting $FAMILY / angle_${ANGLE}"
            python3 evaluate_force_displacement_scripts/generate_final_plots.py \
                --family "$FAMILY" \
                --angle "$ANGLE" \
                --pkl_path "$PKL_PATH" \
                --outdir "$OUTDIR"
        else
            echo "  [WARN] No aggregated results found for $FAMILY / angle_${ANGLE}"
            echo "         Expected: $PKL_PATH"
        fi

    done
done

echo ""
echo "Final plots generated in:"
echo "  comparison_plots/{family}_angle_{X}/"
echo ""

