#!/bin/bash
set -e

# ============================================================================
# CLEANUP ONLY: Remove all family directories
# This script only cleans up - it does NOT run the workflow
# Use this when you want to manually clean before running workflow separately
#
# Usage: ./cleanup_families.sh
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
    echo "  ./cleanup_families.sh"
    exit 1
fi

cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     CLEANUP: Remove All Family Directories                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Working directory: $SCRIPT_DIR"
echo ""

# ============================================================================
# Safety Check: Confirm with user
# ============================================================================
echo "⚠️  WARNING: This will PERMANENTLY DELETE the following directories:"
echo "   - soft/"
echo "   - stiff/"
echo "   - initial/"
echo ""
echo "This includes all results, intermediate files, and logs."
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [[ ! "$CONFIRM" == "yes" ]]; then
    echo ""
    echo "❌ Cleanup cancelled by user"
    exit 0
fi

echo ""

# ============================================================================
# Remove All Family Directories
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "Removing family directories..."
echo "════════════════════════════════════════════════════════════════"
echo ""

FAMILIES=(soft stiff initial)
TOTAL_SIZE=0

for FAMILY in "${FAMILIES[@]}"; do
    if [ -d "$FAMILY" ]; then
        # Calculate size before deletion
        SIZE=$(du -sh "$FAMILY" 2>/dev/null | cut -f1)
        echo "  Removing: $FAMILY/ (size: $SIZE)"
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
# Verify Cleanup
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "Verification:"
echo "════════════════════════════════════════════════════════════════"
echo ""

REMAINING=0
for FAMILY in "${FAMILIES[@]}"; do
    if [ -d "$FAMILY" ]; then
        echo "  ⚠️  $FAMILY/ still exists!"
        REMAINING=$((REMAINING + 1))
    else
        echo "  ✓ $FAMILY/ removed"
    fi
done

echo ""

if [ $REMAINING -eq 0 ]; then
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     CLEANUP COMPLETED SUCCESSFULLY!                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Next steps:"
    echo "  1. Run workflow (will auto-create directories):"
    echo "     ./run_workflow.sh all all"
    echo ""
    echo "  2. Or use the combined setup+run script:"
    echo "     ./setup_and_run.sh all all"
else
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     CLEANUP INCOMPLETE!                                      ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Some directories could not be removed. Check permissions."
    exit 1
fi
