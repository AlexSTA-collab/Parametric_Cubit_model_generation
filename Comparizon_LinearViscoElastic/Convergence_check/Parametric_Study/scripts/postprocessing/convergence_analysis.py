#!/usr/bin/env python3
"""
Parametrized Convergence Analysis Script
========================================

Usage:
    python3 convergence_analysis.py <family> <angle> [error_type]

Examples:
    python3 convergence_analysis.py stiff 0
    python3 convergence_analysis.py initial 10 L1
    python3 convergence_analysis.py soft 0 L2

Arguments:
    family      : Material family (stiff, initial, soft)
    angle       : Angle value (0, 10, etc.)
    error_type  : Optional. Error metric to use (L1, L2, relL1, relL2). Default: L1

This script performs convergence analysis by comparing Interface models
with Full Cauchy reference models across different mesh resolutions.
"""

import sys
import pickle
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==================================================
# MATPLOTLIB PUBLICATION-QUALITY SETTINGS
# ==================================================
plt.rcParams.update({
    "text.usetex": True,                    # Use LaTeX for all text
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "font.size": 11,
    "axes.labelsize": 14,                   # Axis label font size
    "axes.titlesize": 14,
    "xtick.labelsize": 12,                  # Tick label font size
    "ytick.labelsize": 12,
    "legend.fontsize": 11,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "savefig.format": "pdf",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
    "axes.linewidth": 1.0,
    "xtick.major.width": 1.0,
    "ytick.major.width": 1.0,
    "xtick.minor.width": 0.8,
    "ytick.minor.width": 0.8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "lines.linewidth": 2.0,
    "lines.markersize": 7,
})

# ==================================================
# CONFIGURATION
# ==================================================
EPS = 1e-14  # to avoid division by zero
ALL_ERROR_TYPES = ["L1", "L2", "relL1", "relL2"]

# ==================================================
# HELPER FUNCTIONS
# ==================================================
def load_pickle(path):
    with open(path, "rb") as f:
        return pickle.load(f)

def save_pickle(data, path):
    with open(path, "wb") as f:
        pickle.dump(data, f)
    print(f"   💾 Pickled data saved: {path}")

def compute_error_fields(field_full, field_int, order):
    diff = field_full - field_int
    abs_err_field = np.linalg.norm(diff, ord=order, axis=1)
    full_mag = np.linalg.norm(field_full, ord=order, axis=1)
    rel_err_field = abs_err_field / (full_mag + EPS)
    return abs_err_field, full_mag, rel_err_field

def get_coordinate_field(data, possible_keys):
    for key in possible_keys:
        if key in data:
            return data[key]
    raise KeyError(f"None of {possible_keys} found in data keys: {list(data.keys())}")

def parse_h_angle(name):
    """Parse h and angle values from filename, handling multiple formats."""
    import re
    # Match h, angle, m, n in the filename, regardless of order
    pattern = r"_h(?P<h>[^_]+)_angle_(?P<angle>[^_]+)_m_(?P<m>[^_]+)_n_(?P<n>[^_.]+)"
    match = re.search(pattern, name)
    if match:
        try:
            h_val = float(match.group("h"))
            angle_val = float(match.group("angle"))
            m_val = match.group("m")
            n_val = match.group("n")
            return h_val, angle_val, m_val, n_val
        except ValueError:
            pass
    print(f"   ⚠️  Could not parse h/angle/m/n from filename: {name}")
    return None, None, None, None

def plot_error_field(centers, field, vmin=None, vmax=None):
    tol = 1e-6
    x_coords = centers[:, 0]
    y_coords = centers[:, 1]
    x_unique = np.unique(np.round(x_coords / tol) * tol)
    y_unique = np.unique(np.round(y_coords / tol) * tol)
    nx, ny = len(x_unique), len(y_unique)

    field_log = np.log10(np.clip(field, EPS, None))
    plt.figure(figsize=(7, 6))
    if ny * nx == len(field):
        Z = np.full((ny, nx), np.nan)
        for i in range(len(x_coords)):
            x_idx = np.where(x_unique == np.round(x_coords[i] / tol) * tol)[0][0]
            y_idx = np.where(y_unique == np.round(y_coords[i] / tol) * tol)[0][0]
            Z[y_idx, x_idx] = field_log[i]
        X, Y = np.meshgrid(x_unique, y_unique)
        pc = plt.pcolormesh(X, Y, Z, shading="auto", cmap="plasma", vmin=vmin, vmax=vmax)
    else:
        pc = plt.scatter(
            x_coords, y_coords, c=field_log, cmap="plasma", s=50, alpha=0.85,
            vmin=vmin, vmax=vmax
        )
    plt.xlabel(r"$x$")
    plt.ylabel(r"$y$")
    plt.axis("equal")
    
    # Limit number of ticks
    ax = plt.gca()
    ax.locator_params(axis='x', nbins=5)
    ax.locator_params(axis='y', nbins=5)
    
    plt.tight_layout()
    return pc

def plot_convergence(h_values, mean_errors, quantity_name, quantity_units, error_type, out_dir, family, angle):
    """
    Plot convergence with publication quality settings.
    Also pickles the (h_values, mean_errors) data.
    """
    fig, ax = plt.subplots(figsize=(7, 6))
    
    # Plot data
    ax.loglog(h_values, mean_errors, "o-", lw=2, markersize=7, 
              label=fr"{quantity_name} ({error_type})", color='C0')
    
    # Axis labels
    ax.set_xlabel(r"Layer thickness $h$ [mm]", fontsize=14)
    
    # Create appropriate ylabel based on error type
    if error_type.lower() in ["l1", "l2"]:
        ylabel = fr"Mean {error_type} error {quantity_units}"
    else:  # relL1, relL2
        ylabel = fr"Mean {error_type} error"
    ax.set_ylabel(ylabel, fontsize=14)
    
    # Compute convergence rate
    coeffs = np.polyfit(np.log(h_values), np.log(mean_errors), 1)
    rate = coeffs[0]
    
    # Add convergence rate and family/angle info to title
    ax.set_title(fr"{family.capitalize()} - Angle {angle}° - {quantity_name} ({error_type}), rate $\approx {rate:.2f}$", 
                 fontsize=13)
    
    # Set tick parameters
    ax.tick_params(axis='both', which='major', labelsize=12)
    ax.tick_params(axis='both', which='minor', labelsize=10)
    ax.grid(True, which='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.legend(loc='best', frameon=True, framealpha=0.9)
    
    plt.tight_layout()
    
    # Save figure
    sanitized_quantity = quantity_name.replace(" ", "_").replace("[", "").replace("]", "")
    pdf_name = f"convergence_{sanitized_quantity}_{error_type}.pdf"
    pdf_path = out_dir / pdf_name
    plt.savefig(pdf_path, bbox_inches="tight", dpi=300)
    print(f"   📊 Saved: {pdf_path}")
    plt.close(fig)
    
    # Pickle the data
    pickle_name = f"convergence_{sanitized_quantity}_{error_type}.pkl"
    pickle_path = out_dir / pickle_name
    save_pickle({"h": h_values, "error": mean_errors, "rate": rate}, pickle_path)

def process_quantity(interface_cases_dir, full_cases_dir, quantity_prefix, quantity_name, 
                     quantity_units, error_type, out_dir, family, angle, m, n):
    """
    Process a single quantity (displacement jump or traction jump) for all Interface resolutions.
    Files are named like: displacement_jump_h0.010_angle_0.0.pkl
    """
    # Only print reference and interface file paths
    
    # Find reference Full model file (h=0.01) for this quantity
    # Try to match n in both scientific and float notation, and with/without trailing zeros
    n_variants = [n]
    try:
        n_float = float(n)
        n_variants.append(f"{n_float:.0e}")
        n_variants.append(f"{n_float:.1e}")
        n_variants.append(str(n_float))
        n_variants.append(str(int(n_float)))
    except Exception:
        pass
    n_variants = list(set(n_variants))
    full_patterns = []
    for n_var in n_variants:
        full_patterns.extend([
            f"{quantity_prefix}_h0.010_angle_{angle}_m_{m}_n_{n_var}.pkl",
            f"{quantity_prefix}_h0.01_angle_{angle}_m_{m}_n_{n_var}.pkl",
            f"{quantity_prefix}_h0.010_angle_{float(angle):.1f}_m_{m}_n_{n_var}.pkl",
            f"{quantity_prefix}_h0.010_angle_{int(angle)}_m_{m}_n_{n_var}.pkl",
            f"{quantity_prefix}_h0.010_angle_{str(angle)}_m_{m}_n_{n_var}.pkl",
        ])
    
    full_file = None
    for pattern in full_patterns:
        full_files = list(full_cases_dir.glob(pattern))
        if full_files:
            full_file = full_files[0]
            break
    
    if not full_file:
        print(f"❌ ERROR: No reference Full model found for {quantity_name}, angle {angle}")
        print(f"   Searched in: {full_cases_dir}")
        return
    print(f"REFERENCE FILE PATH: {full_file}")
    
    # Find all Interface model files for this quantity
    # Try to match n in both scientific and float notation, and with/without trailing zeros
    n_variants = [n]
    try:
        n_float = float(n)
        n_variants.append(f"{n_float:.0e}")
        n_variants.append(f"{n_float:.1e}")
        n_variants.append(str(n_float))
        n_variants.append(str(int(n_float)))
    except Exception:
        pass
    n_variants = list(set(n_variants))
    interface_patterns = []
    for n_var in n_variants:
        interface_patterns.extend([
            f"{quantity_prefix}_h0.*_angle_{angle}_m_{m}_n_{n_var}.pkl",
            f"{quantity_prefix}_h0.*_angle_{float(angle):.1f}_m_{m}_n_{n_var}.pkl",
            f"{quantity_prefix}_h0.*_angle_{int(angle)}_m_{m}_n_{n_var}.pkl",
            f"{quantity_prefix}_h0.*_angle_{str(angle)}_m_{m}_n_{n_var}.pkl",
        ])
    
    interface_files = []
    for pattern in interface_patterns:
        files = list(interface_cases_dir.glob(pattern))
        interface_files.extend(files)
    
    # Remove duplicates
    interface_files = list(set(interface_files))
    
    if not interface_files:
        print(f"❌ ERROR: No Interface models found for {quantity_name}, angle {angle}")
        return
    print("INTERFACE FILES:")
    for f in interface_files:
        print(f"  {f}")
    
    # Load reference Full model
    full_data = load_pickle(full_file)
    
    # The data key in the pickle is the quantity prefix
    field_full = full_data[quantity_prefix]
    
    # (centers_full assignment removed; not used)
    
    # Prepare storage
    h_values = []
    mean_abs_errors = []
    mean_rel_errors = []
    
    # Determine norm order
    order = 1 if error_type.upper() in ["L1", "RELL1"] else 2
    
    # Process each Interface resolution
    for int_file in sorted(interface_files):
        h_val, angle_val, m_val, n_val = parse_h_angle(int_file.name)
        # Skip if parsing failed
        if h_val is None or angle_val is None:
            continue
        # Load Interface data
        int_data = load_pickle(int_file)
        field_int = int_data[quantity_prefix]
        # (centers_int assignment removed; not used)
        # Compute errors
        abs_err_field, full_mag, rel_err_field = compute_error_fields(field_full, field_int, order)
        # Store mean errors
        h_values.append(h_val)
        mean_abs_errors.append(np.mean(abs_err_field))
        mean_rel_errors.append(np.mean(rel_err_field))
        print(f"h={h_val:6.3f}: mean_abs_err={mean_abs_errors[-1]:.6e}, mean_rel_err={mean_rel_errors[-1]:.6e}")
    
    # Convert to arrays and sort by h
    h_arr = np.array(h_values)
    sort_idx = np.argsort(h_arr)
    h_sorted = h_arr[sort_idx]
    abs_sorted = np.array(mean_abs_errors)[sort_idx]
    rel_sorted = np.array(mean_rel_errors)[sort_idx]
    
    # Plot and save based on error type
    if error_type.upper() in ["L1", "L2"]:
        plot_convergence(h_sorted, abs_sorted, quantity_name, quantity_units, 
                        error_type, out_dir, family, angle)
    else:  # relL1, relL2
        plot_convergence(h_sorted, rel_sorted, quantity_name, "", 
                        error_type, out_dir, family, angle)
    
    # Only print reference and interface file paths above

# ==================================================
# MAIN ANALYSIS FUNCTION
# ==================================================
def run_convergence_analysis(family, angle, m, n, error_type="L1"):
    """
    Run convergence analysis for a specific family and angle.
    
    Parameters:
    -----------
    family : str
        Material family (stiff, initial, soft)
    angle : int or float
        Angle value (0, 10, etc.)
    error_type : str
        Error metric (L1, L2, relL1, relL2)
    """
    print("\n" + "="*70)
    print(f"  CONVERGENCE ANALYSIS: {family.upper()} - Angle {angle}° - m {m} - n {n}")
    print("="*70)
    
    # Setup paths relative to script location (go up to Parametric_Study root)
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent.parent  # scripts/postprocessing -> scripts -> Parametric_Study
    family_angle_m_n_dir = base_dir / family / f"angle_{angle}"/f"m_{m}"/f"n_{n}"
    
    # Define case directories
    full_cases_dir = family_angle_m_n_dir / "Full_layer_models" / "cases"
    interface_cases_dir = family_angle_m_n_dir / "Interface_models" / "cases"
    out_dir = family_angle_m_n_dir / "comparison_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate directories exist
    print(f"DEBUG: Checking existence of {full_cases_dir} -> {full_cases_dir.exists()}")
    if not full_cases_dir.exists():
        print(f"❌ ERROR: Full cases directory not found: {full_cases_dir}")
        sys.exit(1)
    if not interface_cases_dir.exists():
        print(f"❌ ERROR: Interface cases directory not found: {interface_cases_dir}")
        sys.exit(1)
    
    print(f"\n📁 Full cases directory: {full_cases_dir}")
    print(f"📁 Interface cases directory: {interface_cases_dir}")
    
    # Process both quantities
    print("\n" + "="*70)
    print("  PROCESSING DISPLACEMENT JUMPS")
    print("="*70)
    process_quantity(
        interface_cases_dir, full_cases_dir,
        quantity_prefix="displacement_jump",
        quantity_name="Displacement jump",
        quantity_units="[mm]",
        error_type=error_type,
        out_dir=out_dir,
        family=family,
        angle=angle,
        m = m,
        n = n
    )
    
    print("\n" + "="*70)
    print("  PROCESSING TRACTION JUMPS")
    print("="*70)
    process_quantity(
        interface_cases_dir, full_cases_dir,
        quantity_prefix="traction_jump",
        quantity_name="Traction jump",
        quantity_units="[MPa]",
        error_type=error_type,
        out_dir=out_dir,
        family=family,
        angle=angle,
        m = m,
        n = n 
    )
    
    print("\n" + "="*70)
    print(f"  ✅ CONVERGENCE ANALYSIS COMPLETE: {family.upper()} - Angle {angle}°c - m {m} - n {n}")
    print(f"  📂 Results saved to: {out_dir}")
    print("="*70 + "\n")

# ==================================================
# MAIN ENTRY POINT
# ==================================================
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n❌ ERROR: Insufficient arguments")
        print("\nUsage: python3 convergence_analysis.py <family> <angle>")
        print("\nExamples:")
        print("  python3 convergence_analysis.py stiff 0 all all")
        print("  python3 convergence_analysis.py initial 10 all all")
        print("\nNote: All error types (L1, L2, relL1, relL2) are computed automatically")
        sys.exit(1)
    
    family = sys.argv[1].lower()
    
    try:
        angle = int(sys.argv[2])
    except ValueError:
        try:
            angle = float(sys.argv[2])
        except ValueError:
            print(f"❌ ERROR: Invalid angle value: {sys.argv[2]}")
            sys.exit(1)
    
    m = sys.argv[3]
    n = sys.argv[4]

    # Validate inputs
    if family not in ["stiff", "initial", "soft"]:
        print(f"❌ ERROR: Invalid family '{family}'. Must be: stiff, initial, or soft")
        sys.exit(1)
    
    # Run analysis for ALL error types
    print("\n" + "╔" + "="*68 + "╗")
    print(f"║  CONVERGENCE ANALYSIS: {family.upper()} - Angle {angle}° (ALL ERROR TYPES) " + " "*(68-len(f"  CONVERGENCE ANALYSIS: {family.upper()} - Angle {angle}° (ALL ERROR TYPES) ")) + "║")
    print("╚" + "="*68 + "╝\n")
    
    for error_type in ALL_ERROR_TYPES:
        print(f"\n{'═'*70}")
        print(f"  Processing Error Type: {error_type}")
        print(f"{'═'*70}\n")
        run_convergence_analysis(family, angle, m, n, error_type)
    
    print("\n" + "╔" + "="*68 + "╗")
    print(f"║  ✅ ALL ERROR TYPES COMPLETE: {family.upper()} - Angle {angle}°" + " "*(68-len(f"  ✅ ALL ERROR TYPES COMPLETE: {family.upper()} - Angle {angle}°")) + "║")
    print("╚" + "="*68 + "╝\n")
