"""
Generate Full Cauchy (solid layer) model meshes for parametric study.
This script generates meshes with solid elements (no cohesive layer) - geometry only.
Material parameters are applied during Phase 2 when running the parametric study.

IMPORTANT: Only the REFERENCE MESH (h=0.01) is generated for Full Cauchy models!
           Full Cauchy meshes are computationally expensive and serve as the 
           reference/"ground truth" solution. We only need the finest mesh resolution.
           HEIGHT_VALUES_FULL = [0.01] enforces this policy in config_parametric_study.py
"""

import os
from itertools import product
from function_generate_template_file_Full_Cauchy import write_template_file
from function_three_body_cubit_model_Full_Cauchy import generate_cubit_model
from config_parametric_study import ANGLES, HEIGHT_VALUES_FULL, OUTPUT_DIR_FULL

# Parameter sets imported from central configuration
# NOTE: HEIGHT_VALUES_FULL = [0.01] - ONLY reference mesh generated (expensive!)
angles = ANGLES
height_values = HEIGHT_VALUES_FULL  # [0.01] - Single reference mesh only!

# Output directory for Full Cauchy models
output_base = OUTPUT_DIR_FULL
os.makedirs(output_base, exist_ok=True)

print("="*80)
print("PHASE 1: Full Cauchy Model Mesh Generation (REFERENCE MESH ONLY)")
print("="*80)
print(f"Angles: {angles}")
print(f"Heights: {height_values}  ← REFERENCE MESH ONLY (expensive!)")
print(f"Output directory: {output_base}/")
print("")
print("NOTE: Only h=0.01 is generated for Full Cauchy models")
print("      These meshes are computationally expensive and serve as")
print("      the reference solution. Multiple resolutions not needed.")
print("="*80)

# Loop over angle and height → generate mesh for each combination
for angle, height in product(angles, height_values):
    mesh_dir = os.path.join(output_base, f"angle_{angle}", f"height_{height}")
    os.makedirs(mesh_dir, exist_ok=True)
    
    print(f"\n▶ Generating Full Cauchy REFERENCE mesh for angle={angle}°, h={height}")
    print(f"  (This is computationally expensive - only finest mesh needed)")
    
    # Generate Cubit mesh (solid elements only, no cohesive layer)
    generate_cubit_model(angle, height, output_dir=mesh_dir)
    
    # Write template file (with placeholder for material parameters)
    print(f"📝 Writing template file in {mesh_dir}")
    write_template_file(angle=angle, height=height, output_dir=mesh_dir)
    
    print(f"✓ Full Cauchy mesh completed for angle={angle}°, h={height}")

print("\n" + "="*80)
print("✅ All Full Cauchy REFERENCE meshes generated successfully!")
print("="*80)
print(f"\nOutput location: {output_base}/")
print(f"\nMeshes generated: {len(angles)} angles × 1 height = {len(angles)} meshes")
print("(Only h=0.01 reference mesh - avoids expensive computation for unused meshes)")
print("\nNext steps:")
print("  1. Run: ../deploy_meshes.sh")
print("  2. Run: ../run_master_workflow.sh")
