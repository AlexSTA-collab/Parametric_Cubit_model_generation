#!/usr/bin/env bash
set -euo pipefail

# ==================================================
# CONFIGURATION
# ==================================================
SOLVER_ENV="alexandros"
PLOT_ENV="alexandros_Plot"

SOLVER_CMD="edelweissfe"
PVPYTHON_CMD="${PVPYTHON_CMD:-pvpython}"
POST_MODULE_1="Full_Model_Evaluate_traction_jump"
POST_MODULE_2="Full_Model_Evaluate_displacement_jump"

# Target subdirectory
SUBDIR="Full_layer_models"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
TARGET_DIR="${PROJECT_DIR}/${SUBDIR}"

# ==================================================
# FIXED PARAMETERS
# ==================================================
E_M=2e5
E_I=4e3
E_0=4e5
angle=10.0

export E_M E_I E_0 angle

# ==================================================
# CHECKS
# ==================================================
command -v mamba >/dev/null || { echo "ERROR: mamba not found in PATH."; exit 1; }

if ! command -v "$PVPYTHON_CMD" >/dev/null 2>&1; then
  echo "⚠️  '$PVPYTHON_CMD' not found. Falling back to 'python'."
  PVPYTHON_CMD="python"
fi

# ==================================================
# CORE FUNCTION
# ==================================================
run_case () {
  local template_path="$1"
  local work_dir base job_inp height_str

  work_dir="$(dirname "$template_path")"
  base="$(basename "${template_path%.inp}")"

  # Extract h value
  if [[ "$base" =~ _h_([0-9.eE+-]+) ]]; then
    height_str="${BASH_REMATCH[1]}"
  else
    echo "❌ Could not extract height (h) from filename: $base"
    return 1
  fi
  export h="$height_str"

  base_nojob="${base%_job}"
  local job_inp="${work_dir}/${base_nojob}_job.inp"

  echo
  echo "=== Running ${template_path} ==="
  echo "Using parameters: E_M=${E_M}, E_I=${E_I}, E_0=${E_0}, h=${h}, angle=${angle}"

  envsubst '${E_M} ${E_I} ${E_0} ${h} ${angle}' < "$template_path" > "$job_inp"

  ( cd "$work_dir" && mamba run -n "$SOLVER_ENV" "$SOLVER_CMD" "$job_inp" )

  local case_bottom="${work_dir}/Cauchy_Full_model_bottom_${h}.case"
  local case_top="${work_dir}/Cauchy_Full_model_top_${h}.case"

  if [[ -f "$case_bottom" && -f "$case_top" ]]; then
    local out_dir="${work_dir}/cases"
    mkdir -p "$out_dir"
    echo "→ Found matching pair for h=${h}:"
    echo "   bottom: $case_bottom"
    echo "   top:    $case_top"
    echo "→ Running traction jump computation..."

    local tmp_py
    tmp_py="$(mktemp "${work_dir}/tmp_postprocess_XXXX.py")"

    cat > "$tmp_py" <<PYCODE
import sys, traceback, os
from pathlib import Path
print("="*80)
print("[post] Python start OK")
print("[post] sys.executable:", sys.executable)
try:
    from ${POST_MODULE_1} import compute_and_save_traction_jump
    print("[post] Import OK from ${POST_MODULE_1}")
    from ${POST_MODULE_2} import compute_and_save_displacement_jump
    print("[post] Import OK from ${POST_MODULE_2}")

except Exception:
    traceback.print_exc(); sys.exit(1)
case_bottom = Path(r"${case_bottom}")
case_top    = Path(r"${case_top}")
layer_h     = float("${h}")
angle_deg   = float("${angle}")
out_dir     = Path(r"${out_dir}")
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

    print("[post] ✅ Finished successfully.")
except Exception:
    traceback.print_exc(); sys.exit(2)
PYCODE

    echo "[bash] Running postprocess: mamba run -n \"$PLOT_ENV\" \"$PVPYTHON_CMD\" \"$tmp_py\""
    ( cd "$work_dir" && mamba run -n "$PLOT_ENV" "$PVPYTHON_CMD" "$tmp_py" )
    rm -f "$tmp_py"
  else
    echo "⚠️  Missing .case files for h=${h}"
  fi
}

# ==================================================
# MAIN LOOP
# ==================================================
echo
echo ">>> Entering directory: ${SUBDIR}"
shopt -s nullglob
echo "🧹 Cleaning old *_job.inp files in ${SUBDIR}..."
find "$TARGET_DIR" -maxdepth 1 -type f -name "*_job.inp" -delete

inp_files=("$TARGET_DIR"/*.inp)
inp_files=("${inp_files[@]//*_job.inp/}")

if (( ${#inp_files[@]} == 0 )); then
  echo "No .inp templates found in ${SUBDIR}, skipping."
else
  for inp in "${inp_files[@]}"; do
    run_case "$inp"
  done
fi

echo
echo "✅ All templates in ${SUBDIR} processed and postprocessed."

