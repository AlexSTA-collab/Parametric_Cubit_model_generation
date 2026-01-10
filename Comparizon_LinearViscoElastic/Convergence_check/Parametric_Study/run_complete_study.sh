#!/bin/bash
set -e

# ============================================================================
# COMPLETE PARAMETRIC STUDY WORKFLOW
# This script runs the entire parametric study from start to finish:
#   1. Generate meshes for all angles (ONE-TIME - if not already done)
#   2. Run FE analyses for all families and angles
#   3. Generate cross-family comparative plots
# 
# Usage: ./run_complete_study.sh
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     COMPLETE PARAMETRIC STUDY WORKFLOW                       ║"
echo "║     Mesh Generation → Analyses → Comparative Plots           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1: Generate Meshes (if not already done)
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 1/3: Checking Mesh Generation"
echo "════════════════════════════════════════════════════════════════"
echo ""

if [ ! -d "mesh_generation/Interface_models/angle_0" ] || [ ! -d "mesh_generation/Interface_models/angle_10" ]; then
    echo "⚠️  Meshes not found - generating now..."
    cd mesh_generation
    if [ -f "./run_mesh_generation.sh" ]; then
        ./run_mesh_generation.sh
        if [ $? -ne 0 ]; then
            echo "❌ Mesh generation failed!"
            exit 1
        fi
    else
        echo "❌ run_mesh_generation.sh not found!"
        exit 1
    fi
    cd ..
    echo "✅ Mesh generation complete"
else
    echo "✅ Meshes already exist in mesh_generation/"
    echo "   (Centralized mesh data - no deployment needed)"
fi

echo ""

# ============================================================================
# STEP 2: Run Analyses for All Families and All Angles
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 2/3: Running FE Analyses (All Families, All Angles)"
echo "════════════════════════════════════════════════════════════════"
echo ""

./run_workflow.sh all all

if [ $? -ne 0 ]; then
    echo "❌ Analyses failed!"
    exit 1
fi

echo ""
echo "✅ All analyses complete"
echo ""

# ============================================================================
# STEP 3: Generate Comparative Plots
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo "STEP 3/3: Generating Cross-Family Comparative Plots"
echo "════════════════════════════════════════════════════════════════"
echo ""

./generate_plots.sh

if [ $? -ne 0 ]; then
    echo "❌ Plot generation failed!"
    exit 1
fi

echo ""
echo "✅ Comparative plots generated"
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     PARAMETRIC STUDY COMPLETE!                               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Results locations:"
echo "  • Individual convergence: {family}/angle_{X}/comparison_results/"
echo "  • Cross-family plots: comparison_plots/angle_{X}/{error_type}/"
echo ""
echo "Architecture:"
echo "  • Mesh data (READ-ONLY): mesh_generation/"
echo "  • Job files + results: {family}/angle_{X}/"
echo ""
echo "Next steps:"
echo "  • Review convergence plots: {family}/angle_{X}/comparison_results/"
echo "  • Review comparative plots: comparison_plots/"
echo "  • Use .pkl files for further analysis"
echo ""
