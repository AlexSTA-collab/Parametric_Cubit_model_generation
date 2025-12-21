#!/bin/bash
# Convenience wrapper for parallel viscoelastic workflow
exec "$(dirname "$0")/scripts/workflow/run_parallel_workflow.sh" "$@"
