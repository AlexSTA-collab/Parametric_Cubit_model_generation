#!/usr/bin/env python3
import pickle
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==================================================
# CONFIGURATION
# ==================================================
SCRIPT_DIR = Path(__file__).resolve().parent

FULL_CASES = SCRIPT_DIR / "Full_layer_models" / "cases"
INTERFACE_CASES = SCRIPT_DIR / "Interface_models" / "cases"
OUT_DIR = SCRIPT_DIR / "comparison_results"
OUT_DIR.mkdir(exist_ok=True)

SHOW_PLOTS = True
EPS = 1e-14  # to avoid division by zero

# Choose error metric: "L1", "L2", or "relL2"
ERROR_TYPE = "L1"  # <--- change here

# ==================================================
# HELPER FUNCTIONS
# ==================================================
def load_pickle(path):
    with open(path, "rb") as f:
        return pickle.load(f)

def compute_error_fields(field_full, field_int):
    """
    Compute per-point absolute and relative error magnitudes.
    Returns:
      abs_err_field : per-point |Δf|_1
      rel_err_field : per-point |Δf|_1 / (|f_full|_1 + EPS)
      diff          : full vector difference field
    """
    diff = field_full - field_int
    abs_err_field = np.linalg.norm(diff, ord=1, axis=1)
    full_mag = np.linalg.norm(field_full, ord=1, axis=1)
    rel_err_field = abs_err_field / (full_mag + EPS)
    return abs_err_field, rel_err_field, diff

def get_coordinate_field(data, possible_keys):
    """Return the first coordinate array that exists in the data."""
    for key in possible_keys:
        if key in data:
            return data[key]
    raise KeyError(f"None of {possible_keys} found in data keys: {list(data.keys())}")

def plot_error_field(centers, field, h_value, angle_deg, quantity_name, label):
    """Plot a log-scaled scalar error field (absolute or relative)."""
    tol = 1e-6
    x_coords = centers[:, 0]
    y_coords = centers[:, 1]
    x_unique = np.unique(np.round(x_coords / tol) * tol)
    y_unique = np.unique(np.round(y_coords / tol) * tol)
    nx, ny = len(x_unique), len(y_unique)

    # Take log10 safely
    field_log = np.log10(np.clip(field, EPS, None))

    plt.figure(figsize=(10, 8))
    if ny * nx == len(field):
        Z = np.full((ny, nx), np.nan)
        for i in range(len(x_coords)):
            x_idx = np.where(x_unique == np.round(x_coords[i] / tol) * tol)[0][0]
            y_idx = np.where(y_unique == np.round(y_coords[i] / tol) * tol)[0][0]
            Z[y_idx, x_idx] = field_log[i]
        X, Y = np.meshgrid(x_unique, y_unique)
        pc = plt.pcolormesh(X, Y, Z, shading="auto", cmap="plasma")
        plt.colorbar(pc, label=f"log₁₀({label})")
    else:
        scatter = plt.scatter(x_coords, y_coords, c=field_log, cmap="plasma", s=50, alpha=0.85)
        plt.colorbar(scatter, label=f"log₁₀({label})")

    plt.title(f"{quantity_name} log error field ({ERROR_TYPE}) (h={h_value}, angle={angle_deg}°)")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.axis("equal")
    plt.tight_layout()

def plot_convergence(h_values, mean_errors, quantity_name):
    """Plot convergence rate on a log–log plot."""
    plt.figure(figsize=(7, 6))
    plt.loglog(h_values, mean_errors, "o-", label=f"{quantity_name} ({ERROR_TYPE})")
    plt.xlabel("Layer thickness h")
    plt.ylabel(f"Mean {ERROR_TYPE} error")
    plt.grid(True, which="both", ls="--", lw=0.5)
    plt.title(f"Convergence of {quantity_name}")

    # Estimate slope (convergence rate)
    coeffs = np.polyfit(np.log(h_values), np.log(mean_errors), 1)
    rate = coeffs[0]
    plt.legend(title=f"Rate ≈ {rate:.2f}")

    out_path = OUT_DIR / f"{quantity_name}_convergence_{ERROR_TYPE}.png"
    plt.savefig(out_path, dpi=150)
    print(f"   💾 Saved convergence plot: {out_path}")

    if SHOW_PLOTS:
        plt.show()
    else:
        plt.close()

# ==================================================
# MAIN COMPARISON
# ==================================================
families = {
    "traction_jump": {
        "coord_keys": ["centers_bottom"],
        "field_key": "traction_jump",
    },
    "displacement_jump": {
        "coord_keys": ["points_bottom", "points_top"],
        "field_key": "displacement_jump",
    },
}

print(f"📊 Using error metric: {ERROR_TYPE}\n")

for quantity, keys in families.items():
    print(f"\n🔍 Comparing {quantity} fields:")
    print(f"   Full-layer:   {FULL_CASES}")
    print(f"   Interface:    {INTERFACE_CASES}\n")

    full_files = {f.name: f for f in FULL_CASES.glob(f"{quantity}*.pkl")}
    interface_files = {f.name: f for f in INTERFACE_CASES.glob(f"{quantity}*.pkl")}
    common_names = sorted(set(full_files.keys()) & set(interface_files.keys()))

    if not common_names:
        print(f"⚠️  No matching '{quantity}' pickle filenames found.")
        continue

    h_values, mean_errors = [], []

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

        try:
            centers = get_coordinate_field(data_full, keys["coord_keys"])
            field_full = data_full[keys["field_key"]]
            field_int = data_int[keys["field_key"]]
        except KeyError as e:
            print(f"   ❌ Missing expected key(s): {e}")
            continue

        # Compute error fields
        abs_err_field, rel_err_field, diff = compute_error_fields(field_full, field_int)

        # Use mean over all points as the model error (for convergence only)
        mean_err = np.mean(abs_err_field)
        mean_rel_err = np.mean(rel_err_field)

        # Select error to plot and store for convergence
        if ERROR_TYPE.lower() == "l1":
            err_value = mean_err
            field_to_plot = abs_err_field
            label = f"|Δ{quantity}|"
        elif ERROR_TYPE.lower() == "l2":
            err_value = np.sqrt(np.mean(abs_err_field**2))
            field_to_plot = abs_err_field
            label = f"|Δ{quantity}|"
        elif ERROR_TYPE.lower() == "rell2":
            err_value = mean_rel_err
            field_to_plot = rel_err_field
            label = f"|Δ{quantity}| / |{quantity}₍full₎|"
        else:
            raise ValueError(f"Unknown ERROR_TYPE '{ERROR_TYPE}' — use 'L1', 'L2', or 'relL2'.")

        print(f"   ✅ Mean {ERROR_TYPE} error = {err_value:.3e}")

        # Parse h and angle from filename
        try:
            h_str = name.split("_h")[1].split("_angle")[0]
            angle_str = name.split("_angle_")[1].split(".pkl")[0]
            h_value = float(h_str)
            print('h_str', h_value)
            angle_deg = float(angle_str)
        except Exception:
            h_value, angle_deg = 0.0, 0.0

        h_values.append(h_value)
        mean_errors.append(err_value)

        # Plot **log-scaled** spatial error field (no averaging!)
        quantity_label = quantity.replace("_", " ").capitalize()
        plot_error_field(centers, field_to_plot, h_value, angle_deg, quantity_label, label)

        out_plot = OUT_DIR / f"{quantity}_{ERROR_TYPE}_logfield_h{h_value:.3f}_angle_{angle_deg:.1f}.png"
        plt.savefig(out_plot, dpi=150)
        print(f"   💾 Saved log error field: {out_plot}")

        if SHOW_PLOTS:
            plt.show()
        else:
            plt.close()

    # Sort and plot convergence (mean error vs. h)
    if h_values:
        h_values, mean_errors = np.array(h_values), np.array(mean_errors)
        order = np.argsort(h_values)
        plot_convergence(h_values[order], mean_errors[order], quantity)

print("\n✅ Finished comparing all quantities and generating log error and convergence plots.")

