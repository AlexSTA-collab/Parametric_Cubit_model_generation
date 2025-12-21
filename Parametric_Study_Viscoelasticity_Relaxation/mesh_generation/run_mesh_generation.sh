#!/bin/bash
# Wrapper script to run mesh generation using Cubit's Python interpreter

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     MESH GENERATION WRAPPER                                ║"
echo "║     Running with Cubit's Python interpreter                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Navigate to mesh_generation directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $(pwd)"
echo ""

# Generate Interface models (with cohesive layer)
echo "═══════════════════════════════════════════════════════════"
echo "STEP 1/2: Generating Interface Model Meshes"
echo "═══════════════════════════════════════════════════════════"
/home/alexsta1993/Downloads/Coreform-Cubit-2025.8+61943-Lin64/Coreform-Cubit-2025.8/bin/coreform_cubit -nographics -nojournal -batch generate_interface_meshes.py
INTERFACE_EXIT=$?

if [ $INTERFACE_EXIT -ne 0 ]; then
    echo "❌ Interface mesh generation failed with exit code $INTERFACE_EXIT"
    exit $INTERFACE_EXIT
fi

echo ""
echo "✅ Interface meshes generated successfully"
echo ""

# Generate Full Cauchy models (no cohesive layer)
echo "═══════════════════════════════════════════════════════════"
echo "STEP 2/2: Generating Full Cauchy Model Meshes"
echo "═══════════════════════════════════════════════════════════"
/home/alexsta1993/Downloads/Coreform-Cubit-2025.8+61943-Lin64/Coreform-Cubit-2025.8/bin/coreform_cubit -nographics -nojournal -batch generate_full_cauchy_meshes.py
FULL_EXIT=$?

if [ $FULL_EXIT -ne 0 ]; then
    echo "❌ Full Cauchy mesh generation failed with exit code $FULL_EXIT"
    exit $FULL_EXIT
fi

echo ""
echo "✅ Full Cauchy meshes generated successfully"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     MESH GENERATION COMPLETED                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Generated meshes are in:"
echo "  - Interface_models/angle_{0,10}/"
echo "  - Full_layer_models/angle_{0,10}/"
echo ""
echo "Next steps:"
echo "  1. Deploy meshes to family directories"
echo "  2. Run analyses with run_master_workflow.sh"
