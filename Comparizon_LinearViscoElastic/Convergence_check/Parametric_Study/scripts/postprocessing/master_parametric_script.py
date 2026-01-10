#!/usr/bin/env python3
import pickle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colormaps
from pathlib import Path
import sys

# Import centralized configuration
# Script is in scripts/postprocessing/, config is in mesh_generation/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "mesh_generation"))
from config_parametric_study import ANGLES, MATERIAL_FAMILIES

# ===========================================================================
# MATPLOTLIB SETTINGS (same publication style as in your script)
# ===========================================================================
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "font.size": 11,
    "axes.labelsize": 14,
    "axes.titlesize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "savefig.format": "pdf",
    "savefig.bbox": "tight",
    "figure.dpi": 100,
})

# ===========================================================================
# CONFIGURATION
# ===========================================================================
# Script is in scripts/postprocessing/, base dir is Parametric_Study/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Material families and angles imported from centralized config
# You can override here if needed for specific comparisons

# Error metrics to compare - ALL types will be processed
ERROR_TYPES = ["L1", "L2", "relL1", "relL2"]

# Quantities to compare
QUANTITIES = ["traction_jump", "displacement_jump"]  # Can be one or both

# Output directory structure: comparison_plots/angle_{X}/{error_type}/
OUTPUT_DIR_BASE = BASE_DIR / "comparison_plots"
OUTPUT_DIR_BASE.mkdir(exist_ok=True)

# Plasma colormap for family differentiation
COLORMAP = colormaps.get_cmap('plasma')


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================
def find_convergence_pickle(folder, quantity, error_type):
    """
    Looks for the convergence pickle produced by convergence_analysis.py
    The pickle is in comparison_results/ directory with format: convergence_{Quantity}_{error_type}.pkl
    """
    # Convert quantity to match pickle naming (e.g., "traction_jump" -> "Traction_jump")
    quantity_formatted = quantity.replace('_', '_').title().replace('_J', '_j')
    # New naming convention: convergence_Traction_jump_L1.pkl
    pattern = f"convergence_{quantity_formatted}_{error_type}.pkl"
    matches = list(folder.glob(pattern))
    if not matches:
        return None
    return matches[0]

def find_all_convergence_pickles(family_dir, quantity, error_type):
    """
    Recursively find all convergence pickles for a family/angle, for all m/n.
    Returns list of (pkl_path, m, n)
    """
    results = []
    for m_dir in family_dir.glob("m_*/"):
        for n_dir in m_dir.glob("n_*/"):
            comp_dir = n_dir / "comparison_results"
            pkl = find_convergence_pickle(comp_dir, quantity, error_type)
            if pkl:
                m_val = m_dir.name.split("m_")[1]
                n_val = n_dir.name.split("n_")[1]
                results.append((pkl, m_val, n_val))
    return results


def load_convergence_data(path):
    with open(path, "rb") as f:
        return pickle.load(f)


# ===========================================================================
# MAIN COMPARISON PLOTS - Loop over ALL error types
# ===========================================================================
for ERROR_TYPE in ERROR_TYPES:
    print(f"\n{'╔'+'═'*68+'╗'}")
    print(f"║  Processing Error Type: {ERROR_TYPE}{' '*(68-len(f'  Processing Error Type: {ERROR_TYPE}'))}║")
    print(f"{'╚'+'═'*68+'╝'}\n")
    
    for QUANTITY in QUANTITIES:
        for angle in ANGLES:
            print(f"\n=== Comparing families: {QUANTITY} at angle = {angle}° ({ERROR_TYPE}) ===\n")

            # Create output directory structure: angle_{X}/{error_type}/
            output_dir = OUTPUT_DIR_BASE / f"angle_{angle}" / ERROR_TYPE
            output_dir.mkdir(parents=True, exist_ok=True)

            plt.figure(figsize=(7, 6))
            
            found_any = False
            
            # Generate colors from plasma colormap
            num_families = len(MATERIAL_FAMILIES)
            colors = [COLORMAP(i / max(1, num_families - 1)) for i in range(num_families)]


            for idx, (fam_name, params) in enumerate(MATERIAL_FAMILIES.items()):
                fam_dir = BASE_DIR / fam_name / f"angle_{angle}"
                all_pickles = find_all_convergence_pickles(fam_dir, QUANTITY, ERROR_TYPE)
                if not all_pickles:
                    print(f"⚠️  Missing convergence pickles for {fam_name}, angle {angle}")
                    print(f"    Expected in: {fam_dir}")
                    continue
                for pkl_path, m_val, n_val in all_pickles:
                    data = load_convergence_data(pkl_path)
                    h = np.array(data.get("h_values", data.get("h", [])))
                    err = np.array(data.get("mean_errors", data.get("error", [])))
                    order = np.argsort(h)
                    h, err = h[order], err[order]
                    E_0_str = f"{params['E_0']:.0e}" if params['E_0'] >= 1 else f"{params['E_0']:.1e}"
                    label = f"{fam_name.capitalize()} ($E_0={E_0_str}$, m={m_val}, n={n_val})"
                    plt.loglog(h, err, "-o", linewidth=2, markersize=7, label=label, color=colors[idx])

                    for ERROR_TYPE in ERROR_TYPES:
                        print(f"\n{'╔'+'═'*68+'╗'}")
                        print(f"║  Processing Error Type: {ERROR_TYPE}{' '*(68-len(f'  Processing Error Type: {ERROR_TYPE}'))}║")
                        print(f"{'╚'+'═'*68+'╝'}\n")
                        for QUANTITY in QUANTITIES:
                            # Collect all (angle, m, n) combinations from all families
                            combo_set = set()
                            for fam_name in MATERIAL_FAMILIES:
                                fam_dir = BASE_DIR / fam_name
                                for angle_dir in fam_dir.glob("angle_*/"):
                                    angle_val = angle_dir.name.split("angle_")[1]
                                    for m_dir in angle_dir.glob("m_*/"):
                                        m_val = m_dir.name.split("m_")[1]
                                        for n_dir in m_dir.glob("n_*/"):
                                            n_val = n_dir.name.split("n_")[1]
                                            combo_set.add((angle_val, m_val, n_val))
                            # Now plot for each (angle, m, n) combo
                            for angle, m, n in sorted(combo_set):
                                print(f"\n=== Comparing families: {QUANTITY} at angle = {angle}°, m={m}, n={n} ({ERROR_TYPE}) ===\n")
                                output_dir = OUTPUT_DIR_BASE / f"angle_{angle}" / f"m_{m}" / f"n_{n}" / ERROR_TYPE
                                output_dir.mkdir(parents=True, exist_ok=True)
                                plt.figure(figsize=(7, 6))
                                found_any = False
                                num_families = len(MATERIAL_FAMILIES)
                                colors = [COLORMAP(i / max(1, num_families - 1)) for i in range(num_families)]
                                for idx, (fam_name, params) in enumerate(MATERIAL_FAMILIES.items()):
                                    comp_dir = BASE_DIR / fam_name / f"angle_{angle}" / f"m_{m}" / f"n_{n}" / "comparison_results"
                                    pkl_path = find_convergence_pickle(comp_dir, QUANTITY, ERROR_TYPE)
                                    if not pkl_path:
                                        print(f"⚠️  Missing convergence pickle for {fam_name}, angle {angle}, m={m}, n={n}")
                                        continue
                                    data = load_convergence_data(pkl_path)
                                    h = np.array(data.get("h_values", data.get("h", [])))
                                    err = np.array(data.get("mean_errors", data.get("error", [])))
                                    order = np.argsort(h)
                                    h, err = h[order], err[order]
                                    E_0_str = f"{params['E_0']:.0e}" if params['E_0'] >= 1 else f"{params['E_0']:.1e}"
                                    label = f"{fam_name.capitalize()} ($E_0={E_0_str}$)"
                                    plt.loglog(h, err, "-o", linewidth=2, markersize=7, label=label, color=colors[idx])
                                    found_any = True
                                    rate = data.get('convergence_rate', data.get('rate', 'N/A'))
                                    rate_str = f"{rate:.2e}" if isinstance(rate, (int, float)) else str(rate)
                                    print(f"   ✓ Loaded {fam_name} angle={angle} m={m} n={n}: {len(h)} data points, rate ≈ {rate_str}")
                                if not found_any:
                                    print(f"   ⚠️  No data found for {QUANTITY}, angle {angle}, m={m}, n={n}. Skipping plot.")
                                    plt.close()
                                    continue
                                quantity_formatted = QUANTITY.replace('_', ' ').title()
                                ylabel = fr"Mean {ERROR_TYPE} error"
                                plt.xlabel(r"Layer thickness $h$ [mm]")
                                plt.ylabel(ylabel)
                                plt.title(fr"{quantity_formatted} comparison at angle {angle}°, m={m}, n={n} ({ERROR_TYPE})")
                                plt.legend()
                                plt.grid(True, alpha=0.3)
                                from matplotlib.ticker import LogLocator
                                plt.gca().xaxis.set_major_locator(LogLocator(base=10.0, numticks=6))
                                plt.gca().yaxis.set_major_locator(LogLocator(base=10.0, numticks=6))
                                out_path = output_dir / f"comparison_{QUANTITY}.pdf"
                                plt.tight_layout()
                                plt.savefig(out_path)
                                plt.close()
                                print(f"   📈 Saved comparison plot: {out_path}")
