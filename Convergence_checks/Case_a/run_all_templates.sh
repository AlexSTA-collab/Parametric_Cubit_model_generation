#!/usr/bin/env bash
set -euo pipefail

# ==================================================
# CONFIGURATION
# ==================================================
SOLVER_ENV="alexandros"              # mamba/conda env for solver (edelweissfe)
PLOT_ENV="alexandros_Plot"           # env for ParaView + numpy/matplotlib

SOLVER_CMD="edelweissfe"             # solver executable
PVPYTHON_CMD="${PVPYTHON_CMD:-pvpython}"  # prefer pvpython, fallback to python
POST_MODULE="Full_Model_Evaluate_traction_jump"  # Python module to import

# Subdirectories containing .inp templates
SUBDIRS=("Full_layer_models" "Interface_models")

# Base directory (where this script lives)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"

# ==================================================
# FIXED PARAMETERS
# ==================================================
E_M=2e5
E_I=4e3
E_0=4e3
angle=10.0      # degrees; used by postprocessing

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

  # Extract h value from template name (e.g. *_h_0.02.inp -> 0.02)
  if [[ "$base" =~ _h_([0-9.eE+-]+) ]]; then
    height_str="${BASH_REMATCH[1]}"
  else
    echo "❌ Could not extract height (h) from filename: $base"
    return 1
  fi

  export h="$height_str"

  # Strip any existing "_job" suffix to avoid repetition
  base_nojob="${base%_job}"
  local job_inp="${work_dir}/${base_nojob}_job.inp"

  echo
  echo "=== Running ${template_path} ==="
  echo "Using parameters: E_M=${E_M}, E_I=${E_I}, E_0=${E_0}, h=${h}, angle=${angle}"

  # 1) Create the parameterized .inp (overwrite existing safely)
  envsubst '${E_M} ${E_I} ${E_0} ${h} ${angle}' < "$template_path" > "$job_inp"

  # 2) Run solver
  ( cd "$work_dir" && mamba run -n "$SOLVER_ENV" "$SOLVER_CMD" "$job_inp" )

  # 3) Postprocess only the matching pair of .case files for this height
  local case_bottom="${work_dir}/Cauchy_Full_model_bottom_${h}.case"
  local case_top="${work_dir}/Cauchy_Full_model_top_${h}.case"

  if [[ -f "$case_bottom" && -f "$case_top" ]]; then
    local out_dir="${work_dir}/cases"
    mkdir -p "$out_dir"
    echo "→ Found matching pair for h=${h}:"
    echo "   bottom: $case_bottom"
    echo "   top:    $case_top"
    echo "→ Running traction jump computation..."

    # --- Write inline Python code to temporary file ---
    local tmp_py
    tmp_py="$(mktemp "${work_dir}/tmp_postprocess_XXXX.py")"

    cat > "$tmp_py" <<PYCODE
import sys, traceback, os
from pathlib import Path

print("="*80)
print("[post] Python start OK")
print("[post] sys.executable:", sys.executable)
print("[post] cwd:", os.getcwd())
print("[post] sys.argv:", sys.argv)

try:
    from ${POST_MODULE} import compute_and_save_traction_jump
    print("[post] Import OK from ${POST_MODULE}")
except Exception:
    print("[post][ERROR] import failed:")
    traceback.print_exc()
    sys.exit(1)

case_bottom = Path(r"${case_bottom}")
case_top    = Path(r"${case_top}")
layer_h     = float("${h}")
angle_deg   = float("${angle}")
out_dir     = Path(r"${out_dir}")
out_dir.mkdir(exist_ok=True)

print("[post] >>> Executing compute_and_save_traction_jump() ...")
try:
    compute_and_save_traction_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        output_dir=str(out_dir),
        plot=True
    )
    print("[post] >>> Finished successfully.")
except Exception:
    print("[post][ERROR] during compute_and_save_traction_jump:")
    traceback.print_exc()
    sys.exit(2)

pkl_files = list(out_dir.glob("*.pkl"))
if pkl_files:
    print("[post] ✅ Created pickle(s):")
    for p in pkl_files:
        print("  -", p)
else:
    print("[post][WARN] No .pkl files found.")
print("="*80)
PYCODE

    echo "[bash] Running postprocess: mamba run -n \"$PLOT_ENV\" \"$PVPYTHON_CMD\" \"$tmp_py\""
    echo "------------------------------------------------------------"
    ( cd "$work_dir" && mamba run -n "$PLOT_ENV" "$PVPYTHON_CMD" "$tmp_py" )

    rm -f "$tmp_py"

  else
    echo "⚠️  Missing .case files for h=${h}"
    echo "    bottom: $case_bottom"
    echo "    top:    $case_top"
  fi
}  # closes run_case

# ==================================================
# MAIN LOOP
# ==================================================
for subdir in "${SUBDIRS[@]}"; do
  full_path="${PROJECT_DIR}/${subdir}"
  echo
  echo ">>> Entering directory: ${subdir}"

  shopt -s nullglob

  # 🧹 Clean up previous auto-generated job files
  echo "🧹 Cleaning old *_job.inp files in ${subdir}..."
  find "$full_path" -maxdepth 1 -type f -name "*_job.inp" -delete

  # Gather .inp templates, excluding old job files
  inp_files=("$full_path"/*.inp)
  inp_files=("${inp_files[@]//*_job.inp/}")

  if (( ${#inp_files[@]} == 0 )); then
    echo "No .inp templates found in ${subdir}, skipping."
    continue
  fi

  for inp in "${inp_files[@]}"; do
    run_case "$inp"
  done
done

echo
echo "✅ All templates processed and matched postprocessing completed."

