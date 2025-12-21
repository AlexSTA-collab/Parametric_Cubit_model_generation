#!/bin/bash
# Convenience wrapper for generating comparative plots
cd "$(dirname "$0")"
exec python3 scripts/postprocessing/master_parametric_script.py "$@"
