import sys, traceback, os
from pathlib import Path
print("="*80)
print("[post] Python start OK")
print("[post] sys.executable:", sys.executable)
try:
    from Full_Model_Evaluate_traction_jump import compute_and_save_traction_jump
    print("[post] Import OK from Full_Model_Evaluate_traction_jump")
except Exception:
    traceback.print_exc(); sys.exit(1)
case_bottom = Path(r"/home/alexsta1993/Documents/STATHAS_VIENNA_POSTDOC/Applications_Examples/EdelweisModels/Cohesive_Zone_models/3D/Three_Body_Cubit/Comparizon_LinearElastic/Convergence_check/Case_a/Full_layer_models/Cauchy_Full_model_bottom_0.01.case")
case_top    = Path(r"/home/alexsta1993/Documents/STATHAS_VIENNA_POSTDOC/Applications_Examples/EdelweisModels/Cohesive_Zone_models/3D/Three_Body_Cubit/Comparizon_LinearElastic/Convergence_check/Case_a/Full_layer_models/Cauchy_Full_model_top_0.01.case")
layer_h     = float("0.01")
angle_deg   = float("10.0")
out_dir     = Path(r"/home/alexsta1993/Documents/STATHAS_VIENNA_POSTDOC/Applications_Examples/EdelweisModels/Cohesive_Zone_models/3D/Three_Body_Cubit/Comparizon_LinearElastic/Convergence_check/Case_a/Full_layer_models/cases")
out_dir.mkdir(exist_ok=True)
try:
    compute_and_save_traction_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        output_dir=str(out_dir),
        plot=True
    )
    compute_and_save_displacement_jump(
        casefile_bottom=str(case_bottom),
        casefile_top=str(case_top),
        layer_height=layer_h,
        angle_deg=angle_deg,
        output_dir=str(out_dir),
        plot=True
    )

    print("[post] ✅ Finished successfully.")
except Exception:
    traceback.print_exc(); sys.exit(2)
