import os
from itertools import product
#from function_generate_template_file_Creep import write_template_file
from function_generate_template_file_Relaxation import write_template_file
from function_three_body_cubit_model import generate_cubit_model
from orientation_fix import reorder_elements

# Parameter sets
angles = [0, 10]#, 20, 30, 40]
mesh_sizes = [1, 0.1]#, 0.05, 0.025, 0.0125, 0.00625]
E0_values = [1e-8]#, 1e-4, 1e-2, 1e0, 1e2, 1e4, 1e8]
h_values = [1e-3]#, 1e-5]#, 1e-8]

# Loop over angle and mesh_size → generate mesh once
for angle, mesh_size in product(angles, mesh_sizes):
    mesh_dir = os.path.join(f"angle_{angle}", f"mesh_{mesh_size}")
    os.makedirs(mesh_dir, exist_ok=True)

    print(f"▶ Generating mesh for angle={angle}, mesh_size={mesh_size}")
    generate_cubit_model(angle, mesh_size, output_dir=mesh_dir)
    # ✅ Fix orientation right after mesh generation
    elem_file = os.path.join(mesh_dir, "include_elset_interface.inp")   # or the actual filename
    if os.path.exists(elem_file):
        reorder_elements(elem_file, elem_file)  # overwrite in place
        print(f"🔄 Reordered elements in {elem_file}")
    
    print(f"📝 Writing template template in {mesh_dir}")
    write_template_file(angle=angle, mesh_size=mesh_size, output_dir=mesh_dir)
    

print("✅ All input files written. Meshes reused per angle/mesh_size.")


