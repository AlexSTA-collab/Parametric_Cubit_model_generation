#!/usr/bin/env python3
import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==================================================
# CONFIGURATION
# ==================================================
# Resolve everything relative to this script's directory
SCRIPT_DIR = Path(__file__).resolve().parent

FULL_CASES = SCRIPT_DIR / "Full_layer_models" / "cases"
INTERFACE_CASES = SCRIPT_DIR / "Interface_models" / "cases"
OUT_DIR = SCRIPT_DIR / "comparison_results"
OUT_DIR.mkdir(exist_ok=True)

SHOW_PLOTS = True

# ==================================================
# HELPER FUNCTIONS
# ==================================================
def load_pickle(path):
    with open(path, "rb") as f:
        return pickle.load(f)

def compute_error_field(traction_full, traction_int):
    """Compute vector difference and its magnitude."""
    diff = traction_full - traction_int
    return np.linalg.norm(diff, axis=1), diff

def plot_error_field(centers, error_field, h_value, angle_deg):
    """Plot error magnitude as structured or scatter grid."""
    tol = 1e-6
    x_coords = centers[:, 0]
    y_coords = centers[:, 1]
    x_unique = np.unique(np.round(x_coords / tol) * tol)
    y_unique = np.unique(np.round(y_coords / tol) * tol)
    nx, ny = len(x_unique), len(y_unique)

    print(f"Grid dimensions: {ny} x {nx} = {ny * nx}")

    plt.figure(figsize=(10, 8))
    if ny * nx == len(error_field):
        print("Data forms a complete structured grid")
        Z = np.full((ny, nx), np.nan)
        for i in range(len(x_coords)):
            x_idx = np.where(x_unique == np.round(x_coords[i] / tol) * tol)[0][0]
            y_idx = np.where(y_unique == np.round(y_coords[i] / tol) * tol)[0][0]
            Z[y_idx, x_idx] = error_field[i]

        X, Y = np.meshgrid(x_unique, y_unique)
        pc = plt.pcolormesh(X, Y, Z, shading="auto", cmap="magma")
        plt.colorbar(pc, label="|Δ Traction Jump|")
        plt.title(f"Traction Jump Error Magnitude (h={h_value}, angle={angle_deg}°)")
    else:
        print("Data does not form a complete structured grid - using scatter plot instead")
        scatter = plt.scatter(
            x_coords, y_coords, c=error_field,
            cmap="magma", s=50, alpha=0.8
        )
        plt.colorbar(scatter, label="|Δ Traction Jump|")
        plt.title(f"Traction Jump Error (Scatter) (h={h_value}, angle={angle_deg}°)")

    plt.xlabel("x")
    plt.ylabel("y")
    plt.axis("equal")
    plt.tight_layout()

# ==================================================
# MAIN COMPARISON
# ==================================================
print(f"🔍 Comparing traction jump fields:")
print(f"   Full-layer:   {FULL_CASES}")
print(f"   Interface:    {INTERFACE_CASES}")
print()

if not FULL_CASES.exists() or not INTERFACE_CASES.exists():
    raise FileNotFoundError("❌ Missing 'cases' subdirectories under Full_layer_models or Interface_models.")

full_files = {f.name: f for f in FULL_CASES.glob("*.pkl")}
interface_files = {f.name: f for f in INTERFACE_CASES.glob("*.pkl")}

common_names = sorted(set(full_files.keys()) & set(interface_files.keys()))

if not common_names:
    print("⚠️  No matching pickle filenames found.")
    exit(0)

for name in common_names:
    f_full = full_files[name]
    f_int = interface_files[name]
    print(f"→ Comparing: {name}")

    try:
        data_full = load_pickle(f_full)
        data_int = load_pickle(f_int)
    except Exception as e:
        print(f"   ❌ Failed to load {name}: {e}")
        continue

    centers = data_full["centers_bottom"]
    traction_full = data_full["traction_jump"]
    traction_int = data_int["traction_jump"]

    # Compute error field
    error_magnitude, error_vec = compute_error_field(traction_full, traction_int)
    mean_err = np.mean(error_magnitude)
    max_err = np.max(error_magnitude)
    rel_err = np.linalg.norm(error_magnitude) / (np.linalg.norm(np.linalg.norm(traction_full, axis=1)) + 1e-12)

    print(f"   ✅ Mean |Δt|={mean_err:.3e}, Max |Δt|={max_err:.3e}, Rel L2={rel_err:.3e}")

    # Parse h and angle from filename
    try:
        h_str = name.split("_h")[1].split("_angle")[0]
        angle_str = name.split("_angle_")[1].split(".pkl")[0]
        h_value = float(h_str)
        angle_deg = float(angle_str)
    except Exception:
        h_value, angle_deg = 0.0, 0.0

    # Plot error field
    plot_error_field(centers, error_magnitude, h_value, angle_deg)

    out_plot = OUT_DIR / f"error_field_h{h_value:.3f}_angle_{angle_deg:.1f}.png"
    plt.savefig(out_plot, dpi=150)
    print(f"   💾 Saved plot: {out_plot}")

    if SHOW_PLOTS:
        plt.show()
    else:
        plt.close()

print("\n✅ Finished comparing all matching cases.")

