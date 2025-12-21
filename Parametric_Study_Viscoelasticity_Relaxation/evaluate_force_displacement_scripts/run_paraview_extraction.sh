#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WORK_DIR="$1"
OUT_DIR="$2"
E_M="$3"
E_I="$4"
E_0="$5"
H="$6"
M="$7"
N="$8"
FAMILY="$9"
ANGLE="${10}"

cd "$WORK_DIR"

mamba run -n alexandros_Plot pvpython "${SCRIPT_DIR}/extract_parametric_curves.py" \
    --E_M "$E_M" \
    --E_I "$E_I" \
    --E_0 "$E_0" \
    --h "$H" \
    --m_Ju "$M" \
    --n_Ju "$N" \
    --out_dir "$OUT_DIR" \
    --work_dir "$WORK_DIR"
