import os
from itertools import product
from function_generate_input_file import write_input_file
from function_three_body_cubit_model import generate_cubit_model

# Parameter sets
angles = [0, 10, 20, 30, 40]
mesh_sizes = [1, 0.1, 0.05, 0.025, 0.0125, 0.00625]
E0_values = [1e-8, 1e-4, 1e-2, 1e0, 1e2, 1e4, 1e8]
h_values = [1e-3, 1e-5, 1e-8]

# Loop over angle and mesh_size → generate mesh once
for angle, mesh_size in product(angles, mesh_sizes):
    mesh_dir = os.path.join(f"angle_{angle}", f"mesh_{mesh_size}")
    os.makedirs(mesh_dir, exist_ok=True)

    print(f"▶ Generating mesh for angle={angle}, mesh_size={mesh_size}")
    generate_cubit_model(angle, mesh_size, output_dir=mesh_dir)

    # Now loop over all combinations of E0 and h for this mesh
    for E0, h in product(E0_values, h_values):
        input_dir = os.path.join(mesh_dir, f"E0_{E0:.0e}", f"h_{h:.0e}")
        os.makedirs(input_dir, exist_ok=True)

        print(f"📝 Writing input file in {input_dir}")
        write_input_file(E0, h, angle=angle, mesh_size=mesh_size, output_dir=input_dir)

print("✅ All input files written. Meshes reused per angle/mesh_size.")


