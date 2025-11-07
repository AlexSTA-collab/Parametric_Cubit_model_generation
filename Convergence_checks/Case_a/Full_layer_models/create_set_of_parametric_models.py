import os
import sys
import subprocess
from itertools import product
from function_generate_template_file_Full_Cauchy import write_template_file
from function_three_body_cubit_model_Full_Cauchy import generate_cubit_model

# Parameter sets
angles = [10]
E0_values = [1e-8, 1e8]
height_values = [1e-1, 8e-2, 6e-2, 4e-2, 2e-2, 1e-2]

POSTPROCESS_SCRIPT = os.path.abspath("postprocess_elsets_from_nodesets.py")

# Loop over angle and mesh_size → generate mesh once
for angle, height in product(angles, height_values):
    mesh_dir = os.path.join(f"angle_{angle}", f"height_{height}")
    os.makedirs(mesh_dir, exist_ok=True)

    print(f"▶ Generating mesh for angle={angle}, height_values={height}")
    generate_cubit_model(angle, height, output_dir=mesh_dir)
    # ✅ Fix orientation right after mesh generation
    elem_file = os.path.join(mesh_dir, "include_elset_interface.inp")   # or the actual filename
    
    # 🔧 subprocess postprocess step
    print(f"🔧 Postprocessing element sets in {mesh_dir} ...")
    cmd = [
        sys.executable,              # ensures same interpreter/env
        POSTPROCESS_SCRIPT,
        mesh_dir,
        "--elset-files",
        "include_elset_bottom.inp",
        "include_elset_top.inp",
        "include_elset_interface.inp",
        "--only-prefixes",
        "top",
        "bottom",
        "--mode",
        "any",
    ]
    try:
        subprocess.run(cmd, check=True)
        # If you prefer quiet:
        # subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print("❌ Postprocess failed:", e)
        raise

    print(f"📝 Writing template template in {mesh_dir}")
    write_template_file(angle=angle, height=height, output_dir=mesh_dir)

print("✅ All input files written. Meshes reused per angle/mesh_size.")

