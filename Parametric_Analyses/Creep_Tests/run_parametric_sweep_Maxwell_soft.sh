#!/usr/bin/env bash
set -euo pipefail

# =======================
# Config (edit as needed)
# =======================
SOLVER_ENV="alexandros"
PLOT_ENV="alexandros_Plot"
SOLVER_CMD="edelweissfe"          # your solver launcher
SOLVER_ARGS=("job.inp")           # how your solver expects the input

POST_PY_NAME="Paraview_plot_Extraction_script.py"   # new Python script instead of .ipynb

# Parameter grids
E_M_vals=(1.0)
E_I_vals=(1.0)
E_0_vals=(1e-4)
#h_vals=(1e-1 1e-3 1e-5 1e-7)
h_vals=(1e-7)

#n_Ju_vals=(1e-8 1e-6 1e-4)
n_Ju_vals=(1e-6)
m_Ju_vals=(1e-2)
#n_Js_vals=(1e8 1e10 1e12)
n_Js_vals=(1e8)
#m_Js_vals=(1e-5 1e-3 1e-1 1e1)
m_Js_vals=(1e-5)

# =======================
# Paths & checks
# =======================
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
E_0_input="${1:-1e-4}"             # default E_0 if not passed
WORK_DIR="${2:-$PWD}"              # pass /path/to/inputs as 2nd arg, defaults to CWD
OUT_DIR="${WORK_DIR}/out_E0_${E_0_input}"
mkdir -p "$OUT_DIR"

TEMPLATE="${WORK_DIR}/Maxwell_Template_Creep_three_body_model_angle_10_n_0.1.inp"

[[ -f "$TEMPLATE" ]] || { echo "ERROR: $TEMPLATE not found." >&2; exit 1; }

# Find Python post script
if   [[ -f "${WORK_DIR}/${POST_PY_NAME}" ]]; then POST_PY="${WORK_DIR}/${POST_PY_NAME}"
elif [[ -f "${SCRIPT_DIR}/${POST_PY_NAME}" ]]; then POST_PY="${SCRIPT_DIR}/${POST_PY_NAME}"
else
  echo "ERROR: ${POST_PY_NAME} not found in WORK_DIR or SCRIPT_DIR." >&2; exit 1
fi

command -v mamba >/dev/null || { echo "ERROR: mamba not found in PATH"; exit 1; }

# =======================
# Core runner
# =======================
run_case () {
  local E_M="$1" E_I="$2" E_0="$3" h="$4" m_Ju="$5" n_Ju="$6" m_Js="$7" n_Js="$8"

  # Filename prefix only
  local run_tag="E0_${E_0}_h_${h}_mJu_${m_Ju}_nJu_${n_Ju}_mJs_${m_Js}_nJs_${n_Js}"

  # 1) Create job.inp in WORK_DIR from template
  export E_M E_I E_0 h m_Ju n_Ju m_Js n_Js
  envsubst '${E_M} ${E_I} ${E_0} ${h} ${m_Ju} ${n_Ju} ${m_Js} ${n_Js}' \
  < "$TEMPLATE" > "${WORK_DIR}/job.inp"

  # 2) Timestamp marker to detect new outputs
  local tsfile="${WORK_DIR}/.ts_${run_tag}"
  : > "$tsfile"

  # 3) Run solver IN WORK_DIR
  ( cd "$WORK_DIR" && mamba run -n "$SOLVER_ENV" "$SOLVER_CMD" "${SOLVER_ARGS[@]}" )

  # 4) Find newest .case produced after the timestamp
  local case_file=""
  while IFS= read -r -d '' f; do
    [[ -z "$case_file" || "$f" -nt "$case_file" ]] && case_file="$f"
  done < <(find "$WORK_DIR" -maxdepth 1 -type f -name "*.case" -newer "$tsfile" -print0)
  rm -f "$tsfile"

  # 5) Run your Python post-processing script
  echo "Running ParaView extraction for ${run_tag}..."
  mamba run -n "$PLOT_ENV" python "$POST_PY" \
    --E_M "$E_M" \
    --E_I "$E_I" \
    --E_0 "$E_0" \
    --h "$h" \
    --m_Ju "$m_Ju" \
    --n_Ju "$n_Ju" \
    --m_Js "$m_Js" \
    --n_Js "$n_Js" \
    --out_dir "$OUT_DIR" \
    --out_prefix "$run_tag" \
    --work_dir "$WORK_DIR" \
    ${case_file:+--case_path "$case_file"}
}

# =======================
# Sweeps
# =======================
for h in "${h_vals[@]}"; do
  for m_Js in "${m_Js_vals[@]}"; do
    for n_Ju in "${n_Ju_vals[@]}"; do
      for n_Js in "${n_Js_vals[@]}"; do
        E_M_fix="${E_M_vals[0]}"
        E_I_fix="${E_I_vals[0]}"
        E_0_fix="${E_0_input}"
        m_Ju_fix="${m_Ju_vals[0]}"
        run_case "$E_M_fix" "$E_I_fix" "$E_0_fix" "$h" "$m_Ju_fix" "$n_Ju" "$m_Js" "$n_Js"
      done
    done
  done
done

echo "Done. Results saved under: ${OUT_DIR}/"

