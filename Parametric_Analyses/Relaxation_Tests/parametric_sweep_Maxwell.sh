#!/usr/bin/env bash
set -euo pipefail

# =======================
# Config (edit as needed)
# =======================
SOLVER_ENV="alexandros"
PLOT_ENV="alexandros_Plot"
SOLVER_CMD="edelweissfe"          # your solver launcher
SOLVER_ARGS=("job.inp")           # how your solver expects the input

POST_NB_NAME="Paraview_Plot_Extraction.ipynb"  # your single notebook

# Parameter grids
E_M_vals=(1.0)
E_I_vals=(1.0)
#E_0_vals=(1e-8 1e8 1e4)
E_0_vals=(1e-8)
#h_vals=(1e-3)
h_vals=(1e-5)

#n_Ju_vals=(1e-8 1e-6 1e-4)
n_Ju_vals=(1e-6)
#m_Ju_vals=(1e-2 1e-1 1e0)
m_Ju_vals=(1e-2)

#n_Js_vals=( 1e8  1e10  1e12)
n_Js_vals=(1e10)
#m_Js_vals=(1e-5  1e-3  1e-1)
m_Js_vals=(1e-5)
# One-at-a-time sweeps use these fixed values:
#n_Ju_fix="${n_Ju_vals[0]}"
#m_Js_fix="${m_Js_vals[0]}"
#n_Js_fix="${n_Js_vals[0]}"
#m_Ju_fix="${m_Ju_vals[0]}"

# =======================
# Paths & checks
# =======================
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
WORK_DIR="${1:-$PWD}"              # pass /path/to/inputs as 1st arg, defaults to CWD
OUT_DIR="${WORK_DIR}/out"
mkdir -p "$OUT_DIR"

TEMPLATE="${WORK_DIR}/Maxwell_Template_Relaxation_three_body_model_angle_10_n_0.1.inp"

[[ -f "$TEMPLATE" ]] || { echo "ERROR: $TEMPLATE not found." >&2; exit 1; }

if   [[ -f "${WORK_DIR}/${POST_NB_NAME}" ]]; then POST_NB="${WORK_DIR}/${POST_NB_NAME}"
elif [[ -f "${SCRIPT_DIR}/${POST_NB_NAME}" ]]; then POST_NB="${SCRIPT_DIR}/${POST_NB_NAME}"
else
  echo "ERROR: ${POST_NB_NAME} not found in WORK_DIR or SCRIPT_DIR." >&2; exit 1
fi

command -v mamba >/dev/null || { echo "ERROR: mamba not found in PATH"; exit 1; }
command -v envsubst >/dev/null || { echo "ERROR: envsubst (gettext) not found"; exit 1; }
mamba run -n "$PLOT_ENV" python -c "import papermill" 2>/dev/null || {
  echo "ERROR: papermill not available in env '$PLOT_ENV' (install: mamba run -n $PLOT_ENV python -m pip install papermill)"; exit 1; }

# =======================
# Core runner
# =======================
run_case () {
  local E_M="$1" E_I="$2" E_0="$3" h="$4" m_Ju="$5" n_Ju="$6" m_Js="$7" n_Js="$8"

  # Filename prefix only
  local run_tag="E0_${E_0}_mJu_${m_Ju}_nJu_${n_Ju}_mJs_${m_Js}_nJs_${n_Js}"

  # 1) Create job.inp in WORK_DIR from template
  export E_M E_I E_0 h m_Ju n_Ju m_Js n_Js
  envsubst '${E_M} ${E_I} ${E_0} ${h} ${m_Ju} ${n_Ju} ${m_Js} ${n_Js}' \
  < "$TEMPLATE" > "${WORK_DIR}/job.inp"


  # 2) Timestamp marker to detect new outputs
  local tsfile="${WORK_DIR}/.ts_${run_tag}"
  : > "$tsfile"

  # 3) Run solver IN WORK_DIR
  ( cd "$WORK_DIR" && mamba run -n "$SOLVER_ENV" "$SOLVER_CMD" "${SOLVER_ARGS[@]}" )

  # 4) Find newest .case produced after the timestamp (optional param)
  local case_file=""
  while IFS= read -r -d '' f; do
    [[ -z "$case_file" || "$f" -nt "$case_file" ]] && case_file="$f"
  done < <(find "$WORK_DIR" -maxdepth 1 -type f -name "*.case" -newer "$tsfile" -print0)
  rm -f "$tsfile"

  # 5) Run your notebook with parameters; no new .ipynb kept
  mamba run -n "$PLOT_ENV" papermill \
    "$POST_NB" /dev/null \
    -p E_M "$E_M" \
    -p E_I "$E_I" \
    -p E_0 "$E_0" \
    -p h "$h" \
    -p m_Ju "$m_Ju" \
    -p n_Ju "$n_Ju" \
    -p m_Js "$m_Js" \
    -p n_Js "$n_Js" \
    -p out_dir "$OUT_DIR" \
    -p out_prefix "$run_tag" \
    -p work_dir "$WORK_DIR" \
    ${case_file:+-p case_path "$case_file"}
}

# =======================
# Sweeps
# =======================
## Sweep 1: E_0 x m_Ju (fix m_Js, n_Js)
#for n_Ju in "${n_Ju_vals[@]}"; do
#  for m_Ju in "${m_Ju_vals[@]}"; do
    # One-at-a-time sweeps use these fixed values:#
#    E_0_fix="${E_0_vals[0]}"
#    n_Js_fix="${n_Js_vals[0]}"
#    m_Js_fix="${m_Js_vals[0]}"  
#    run_case "$E_0_fix" "$m_Ju" "$n_Ju" "$m_Js_fix" "$n_Js_fix"
#  done
#done

## Sweep 2: E_0 x m_Js (fix m_Ju, n_Ju, n_Js)
#for n_Js in "${n_Js_vals[@]}"; do
#  for m_Js in "${m_Js_vals[@]}"; do
#    # One-at-a-time sweeps use these fixed values:
#    E_0_fix="${E_0_vals[1]}"
#    m_Ju_fix="${m_Ju_vals[0]}"  
#   n_Ju_fix="${n_Ju_vals[0]}"
#    run_case "$E_0_fix" "$m_Ju_fix" "$n_Ju_fix" "$m_Js" "$n_Js"
#  done
#done

#3 Sweep 3: n_Js x n_Ju (fix E0, m_Ju, m_Js)
for n_Ju in "${n_Ju_vals[@]}"; do
  for n_Js in "${n_Js_vals[@]}"; do
    # One-at-a-time sweeps use these fixed values:#
    E_M_fix="${E_M_vals[0]}"
    E_I_fix="${E_I_vals[0]}"
    E_0_fix="${E_0_vals[2]}"
    h_fix="${h_vals[0]}"
    m_Ju_fix="${m_Ju_vals[0]}"
    m_Js_fix="${m_Js_vals[0]}"  
    run_case  "$E_M_fix" "$E_I_fix" "$E_0_fix" "$h_fix" "$m_Ju_fix" "$n_Ju" "$m_Js_fix" "$n_Js"
  done
done


echo "Done. Notebook saved outputs under: ${OUT_DIR}/"
