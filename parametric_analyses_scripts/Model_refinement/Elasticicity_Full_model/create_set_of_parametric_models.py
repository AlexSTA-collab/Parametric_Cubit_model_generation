import os
from itertools import product
from function_generate_template_file import write_template_file
from function_three_body_cubit_model import generate_cubit_model
from orientation_fix import reorder_elements

# Parameter sets
angles = [10]#, 20, 30, 40]
#mesh_sizes = [1, 0.1]#, 0.05, 0.025, 0.0125, 0.00625]
E0_values = [1e-8]#, 1e-4, 1e-2, 1e0, 1e2, 1e4, 1e8]
height_values = [1e-3]#, 1e-2, 1e-3]#, 1e-2]#, 1e-2]#, 1e-5]#, 1e-8]

# Loop over angle and mesh_size → generate mesh once
for angle, height in product(angles, height_values):
    mesh_dir = os.path.join(f"angle_{angle}", f"height_{height}")
    os.makedirs(mesh_dir, exist_ok=True)
    for height in height_values:
        print(f"▶ Generating mesh for angle={angle}, and interface layer height={height}")
        generate_cubit_model(angle, height ,output_dir=mesh_dir)
    
        print(f"📝 Writing template template in {mesh_dir}")
        write_template_file(angle=angle, height=height, output_dir=mesh_dir)
    

print("✅ All input files written. Meshes reused per angle/mesh_size.")


