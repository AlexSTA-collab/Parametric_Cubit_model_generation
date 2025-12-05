#!/bin/bash
# Convenience wrapper for main workflow script
exec "$(dirname "$0")/scripts/workflow/run_master_workflow.sh" "$@"
