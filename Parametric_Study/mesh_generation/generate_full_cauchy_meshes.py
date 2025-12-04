"""
Generate Full Cauchy (solid layer) model meshes for parametric study.
This script generates meshes with solid elements (no cohesive layer) - geometry only.
Material parameters are applied during Phase 2 when running the parametric study.
"""

import os
from itertools import product
from function_generate_template_file_Full_Cauchy import write_template_file
from function_three_body_cubit_model_Full_Cauchy import generate_cubit_model

# Parameter sets - geometry only (material parameters in Phase 2)
angles = [10]
height_values = [1e-2]  # Only h=0.01 for Full Cauchy models

# Output directory for Full Cauchy models
output_base = "Full_layer_models"
os.makedirs(output_base, exist_ok=True)

print("="*80)
print("PHASE 1: Full Cauchy Model Mesh Generation")
print("="*80)
print(f"Angles: {angles}")
print(f"Heights: {height_values}")
print(f"Output directory: {output_base}/")
print("="*80)

# Loop over angle and height → generate mesh for each combination
for angle, height in product(angles, height_values):
    mesh_dir = os.path.join(output_base, f"angle_{angle}", f"height_{height}")
    os.makedirs(mesh_dir, exist_ok=True)
    
    print(f"\n▶ Generating Full Cauchy mesh for angle={angle}°, h={height}")
    
    # Generate Cubit mesh (solid elements only, no cohesive layer)
    generate_cubit_model(angle, height, output_dir=mesh_dir)
    
    # Write template file (with placeholder for material parameters)
    print(f"📝 Writing template file in {mesh_dir}")
    write_template_file(angle=angle, height=height, output_dir=mesh_dir)
    
    print(f"✓ Full Cauchy mesh completed for angle={angle}°, h={height}")

print("\n" + "="*80)
print("✅ All Full Cauchy model meshes generated successfully!")
print("="*80)
print(f"\nOutput location: {output_base}/")
print("\nNext steps:")
print("  1. Run: ./copy_meshes_to_shared.sh")
print("  2. Run: ./link_meshes_to_families.sh")
print("  3. Proceed to Phase 2: cd .. && ./run_parametric_study.sh")
