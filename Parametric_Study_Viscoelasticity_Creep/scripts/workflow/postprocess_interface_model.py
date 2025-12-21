import sys, os, traceback
from pathlib import Path
# Ensure evaluation_scripts is in sys.path for imports
eval_scripts_path = os.path.abspath("{EVAL_SCRIPTS_PATH}")
if eval_scripts_path not in sys.path:
    sys.path.insert(0, eval_scripts_path)
from Interface_Model_Evaluate_traction_jump import compute_and_save_traction_jump
from Interface_Model_Evaluate_displacement_jump import compute_and_save_displacement_jump

case_bottom = Path("Cohesive_zone_model_bottom_{H}.case")
case_top = Path("Cohesive_zone_model_top_{H}.case")
layer_h = float("{H}")
angle_deg = float("{ANGLE}")
out_dir = Path("cases")
out_dir.mkdir(exist_ok=True)
try:
    compute_and_save_traction_jump(str(case_bottom), str(case_top), layer_h, angle_deg, str(out_dir), False)
    compute_and_save_displacement_jump(str(case_bottom), str(case_top), layer_h, angle_deg, str(out_dir), False)
except Exception:
    traceback.print_exc(); sys.exit(2)
