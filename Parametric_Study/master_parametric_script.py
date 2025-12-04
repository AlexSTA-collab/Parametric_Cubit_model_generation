#!/usr/bin/env python3
import pickle
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

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
BASE_DIR = Path(__file__).resolve().parent

# Focus on stiff family only for now
MATERIAL_FAMILIES = {
    "stiff":   {"E_M": 2e5, "E_I": 4e3, "E_0": 4e7},
}

# Angles to compare
ANGLES = [10]  # Can add more angles like [0, 10] if needed

# Choose the error metric you want to compare
# Must match "error_TYPE" used in your main post-processing script ("L1", "L2", "relL1", "relL2")
ERROR_TYPE = "L2"     

# Quantities to compare
QUANTITIES = ["traction_jump", "displacement_jump"]  # Can be one or both

OUTPUT_DIR = BASE_DIR / "comparison_plots"
OUTPUT_DIR.mkdir(exist_ok=True)


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================
def find_convergence_pickle(folder, quantity, error_type):
    """
    Looks for the convergence pickle produced by Final_comparizon_convergence_fixed_range_publication.py
    The pickle is in comparison_results/error_{ERROR_TYPE}/ directory
    """
    # Convert quantity to match pickle naming (e.g., "traction_jump" -> "t_i")
    quantity_map = {
        "traction_jump": "t_i",
        "displacement_jump": "u_i"
    }
    pkl_name = quantity_map.get(quantity, quantity)
    
    pattern = f"{pkl_name}_convergence_{error_type}.pkl"
    matches = list(folder.rglob(pattern))
    if not matches:
        return None
    return matches[0]


def load_convergence_data(path):
    with open(path, "rb") as f:
        return pickle.load(f)


# ===========================================================================
# MAIN COMPARISON PLOTS
# ===========================================================================
for QUANTITY in QUANTITIES:
    for angle in ANGLES:
        print(f"\n=== Comparing families: {QUANTITY} at angle = {angle}° ===\n")

        plt.figure(figsize=(7, 6))
        
        found_any = False

        for fam_name, params in MATERIAL_FAMILIES.items():
            # Look for results in family-specific directory
            fam_dir = BASE_DIR / fam_name / f"angle_{angle}" / "comparison_results"
            pkl_path = find_convergence_pickle(fam_dir, QUANTITY, ERROR_TYPE)

            if pkl_path is None:
                print(f"⚠️  Missing convergence pickle for {fam_name}, angle {angle}")
                print(f"    Expected in: {fam_dir}")
                continue

            data = load_convergence_data(pkl_path)

            h = np.array(data["h_values"])
            err = np.array(data["mean_errors"])

            # Optional sorting for safety
            order = np.argsort(h)
            h, err = h[order], err[order]

            # Create label with material parameters
            E_0_str = f"{params['E_0']:.0e}" if params['E_0'] >= 1 else f"{params['E_0']:.1e}"
            label = f"{fam_name.capitalize()} ($E_0={E_0_str}$)"
            
            plt.loglog(h, err, "-o", linewidth=2, markersize=7, label=label)
            found_any = True
            
            print(f"   ✓ Loaded {fam_name}: {len(h)} data points, rate ≈ {data.get('convergence_rate', 'N/A'):.2f}")

        if not found_any:
            print(f"   ⚠️  No data found for {QUANTITY}, angle {angle}. Skipping plot.")
            plt.close()
            continue

        # Labels
        if ERROR_TYPE.lower() in ["l1", "l2"]:
            # Get units from first loaded data
            quantity_units = data.get("quantity_units", "")
            ylabel = fr"Mean {ERROR_TYPE} error {quantity_units}"
        else:
            ylabel = fr"Mean {ERROR_TYPE} error"
        
        plt.xlabel(r"Layer thickness $h$ [mm]")
        plt.ylabel(ylabel)
        
        # Get latex name from data
        quantity_latex = data.get("quantity_name", QUANTITY.replace('_', ' ').title())
        plt.title(fr"{quantity_latex} comparison at angle {angle}°")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Limit ticks
        from matplotlib.ticker import LogLocator
        plt.gca().xaxis.set_major_locator(LogLocator(base=10.0, numticks=6))
        plt.gca().yaxis.set_major_locator(LogLocator(base=10.0, numticks=6))

        # Save
        out_path = OUTPUT_DIR / f"comparison_{QUANTITY}_{ERROR_TYPE}_angle{angle}.pdf"
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()

        print(f"   📈 Saved comparison plot: {out_path}")

print("\n==============================================")
print("🎉 Finished generating common convergence plots!")
print("==============================================\n")
