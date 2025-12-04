#!/usr/bin/env python3
"""
Generate meshes and template files for parametric study.
This script creates meshes for Interface models (with cohesive layer).
"""
import os
from itertools import product
from function_generate_template_file import write_template_file
from function_three_body_cubit_model import generate_cubit_model
from orientation_fix import reorder_elements

# Parameter sets for parametric study
angles = [10]  # Can add more angles: [0, 10]
height_values = [0.1, 0.08, 0.06, 0.04, 0.02, 0.01]  # Layer heights for convergence study (descending order)

print("╔════════════════════════════════════════════════════════════╗")
print("║     MESH GENERATION FOR PARAMETRIC STUDY                   ║")
print("║     Interface Models (with cohesive layer)                 ║")
print("╚════════════════════════════════════════════════════════════╝")
print()
print(f"Angles: {angles}")
print(f"Heights: {height_values}")
print()

# Output to Interface_models subdirectory
base_output_dir = "Interface_models"
os.makedirs(base_output_dir, exist_ok=True)

# Loop over angle and height → generate mesh
for angle, height in product(angles, height_values):
    mesh_dir = os.path.join(base_output_dir, f"angle_{angle}", f"height_{height}")
    os.makedirs(mesh_dir, exist_ok=True)

    print(f"╔════════════════════════════════════════════════════════════╗")
    print(f"║  Generating mesh: angle={angle}°, height={height}")
    print(f"╚════════════════════════════════════════════════════════════╝")
    
    # Generate mesh using Cubit
    print(f"▶ Running Cubit mesh generation...")
    generate_cubit_model(angle, height, output_dir=mesh_dir)
    
    # Fix element orientation
    elem_file = os.path.join(mesh_dir, "include_elset_interface.inp")
    if os.path.exists(elem_file):
        reorder_elements(elem_file, elem_file)  # overwrite in place
        print(f"🔄 Reordered interface elements in {elem_file}")
    
    # Generate template .inp file
    print(f"📝 Writing template file...")
    write_template_file(angle=angle, height=height, output_dir=mesh_dir)
    
    print(f"✅ Completed: angle={angle}°, h={height}")
    print()

print("╔════════════════════════════════════════════════════════════╗")
print("║  ✅ ALL INTERFACE MODEL MESHES GENERATED                   ║")
print("╚════════════════════════════════════════════════════════════╝")
print()
print("Mesh files location:")
for angle in angles:
    for height in height_values:
        print(f"  - Interface_models/angle_{angle}/height_{height}/")
print()
print("Template files location:")
print(f"  - LinearElastic_Interface_Template_three_body_model_angle_*_h_*.inp")
print()
print("Next steps:")
print("  1. Generate Full Cauchy meshes (if needed)")
print("  2. Copy all meshes to shared library: bash copy_meshes_to_shared.sh")
print("  3. Run parametric study: cd .. && bash run_parametric_study.sh")
