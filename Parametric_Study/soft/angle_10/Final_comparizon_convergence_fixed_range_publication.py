#!/usr/bin/env python3
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
SCRIPT_DIR = Path(__file__).resolve().parent

# Point to the actual cases directories in *_templates folders
FULL_CASES = SCRIPT_DIR / "Full_layer_models_templates" / "cases"
INTERFACE_CASES = SCRIPT_DIR / "Interface_models_templates" / "cases"
OUT_DIR = SCRIPT_DIR / "comparison_results"
OUT_DIR.mkdir(exist_ok=True)

SHOW_PLOTS = False  # Set to True for interactive display
EPS = 1e-14  # to avoid division by zero

# All error metrics to process
ERROR_TYPES = ["L1", "L2", "relL1", "relL2"]

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
    h_str = name.split("_h")[1].split("_angle")[0]
    angle_str = name.split("_angle_")[1].split(".pkl")[0]
    return float(h_str), float(angle_str)

def plot_error_field(centers, field, h_value, angle_deg, quantity_name, label, vmin=None, vmax=None):
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

def plot_convergence(h_values, mean_errors, quantity_name, quantity_units, error_type, out_dir):
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
    
    # Add convergence rate to title or legend
    ax.set_title(fr"Convergence: {quantity_name} ({error_type}), rate $\approx {rate:.2f}$", 
                 fontsize=14)
    
    # Set tick parameters
    ax.tick_params(axis='both', which='major', labelsize=12)
    ax.tick_params(axis='both', which='minor', labelsize=10)
    
    # Limit number of ticks for log scale
    from matplotlib.ticker import LogLocator
    ax.xaxis.set_major_locator(LogLocator(base=10.0, numticks=6))
    ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=6))
    
    # Save plot
    out_path = out_dir / f"{quantity_name.replace('$', '').replace('[', '').replace(']', '').replace(' ', '_')}_convergence_{error_type}.pdf"
    plt.tight_layout()
    plt.savefig(out_path, format='pdf', bbox_inches="tight")
    print(f"   💾 Saved convergence plot: {out_path}")
    
    # Pickle the convergence data
    convergence_data = {
        "h_values": h_values,
        "mean_errors": mean_errors,
        "convergence_rate": rate,
        "error_type": error_type,
        "quantity_name": quantity_name,
        "quantity_units": quantity_units
    }
    pickle_path = out_dir / f"{quantity_name.replace('$', '').replace('[', '').replace(']', '').replace(' ', '_')}_convergence_{error_type}.pkl"
    save_pickle(convergence_data, pickle_path)
    
    if SHOW_PLOTS:
        plt.show()
    else:
        plt.close()

# ==================================================
# MAIN COMPARISON
# ==================================================
families = {
    "traction_jump": {"coord_keys": ["centers_bottom"], "field_key": "traction_jump"},
    "displacement_jump": {"coord_keys": ["points_bottom", "points_top"], "field_key": "displacement_jump"},
}

latex_symbols = {"traction_jump": r"$[t_i]$", "displacement_jump": r"$[u_i]$"}
quantity_units = {"traction_jump": r"[MPa]", "displacement_jump": r"[mm]"} 

# Loop over all error types
for ERROR_TYPE in ERROR_TYPES:
    print(f"\n{'='*60}")
    print(f"📊 Processing error metric: {ERROR_TYPE}")
    print(f"{'='*60}\n")
    
    # Create subdirectory for this error type
    error_out_dir = OUT_DIR / f"error_{ERROR_TYPE}"
    error_out_dir.mkdir(exist_ok=True)
    
    for quantity, keys in families.items():
        print(f"\n🔍 Comparing {quantity} fields:")
        print(f"   Full-layer:   {FULL_CASES}")
        print(f"   Interface:    {INTERFACE_CASES}\n")

        latex_label = latex_symbols.get(quantity, "")
        quantity_unit = quantity_units.get(quantity, "")  
        full_files = {f.name: f for f in FULL_CASES.glob(f"{quantity}*.pkl")}
        interface_files = {f.name: f for f in INTERFACE_CASES.glob(f"{quantity}*.pkl")}

        if not full_files or not interface_files:
            print(f"⚠️  Missing data for '{quantity}'. Skipping.")
            continue

        # build per-angle reference
        full_by_angle = {}
        for fname, fpath in full_files.items():
            try:
                h, ang = parse_h_angle(fname)
            except Exception:
                continue
            if ang not in full_by_angle or h < full_by_angle[ang][0]:
                full_by_angle[ang] = (h, fpath)

        if not full_by_angle:
            print(f"⚠️  Could not determine reference full models for {quantity}.")
            continue

        # Determine global color limits
        all_field_values = []
        for name, f_int in interface_files.items():
            try:
                h_i, ang_i = parse_h_angle(name)
                if ang_i not in full_by_angle:
                    continue
                ref_full_path = full_by_angle[ang_i][1]
                ref_full = full_by_angle[ang_i]
                data_full = load_pickle(ref_full_path)
                data_int = load_pickle(f_int)
                field_full = data_full[keys["field_key"]]
                field_int = data_int[keys["field_key"]]
                abs_err_field, _, _ = compute_error_fields(field_full, field_int, 1)
                all_field_values.append(abs_err_field)
            except Exception:
                continue

        if all_field_values:
            all_field_values = np.concatenate(all_field_values)
            global_vmin = np.log10(np.clip(all_field_values.min(), EPS, None))
            global_vmax = np.log10(np.clip(all_field_values.max(), EPS, None))
            print(f"   🎨 Using shared color scale: [{global_vmin:.2f}, {global_vmax:.2f}]")
        else:
            global_vmin = global_vmax = None

        h_values, mean_errors = [], []

        # MAIN COMPARISON LOOP
        for name, f_int in sorted(interface_files.items()):
            print(f"→ Comparing interface model: {name}")
            try:
                h_i, ang_i = parse_h_angle(name)
            except Exception:
                print("   ❌ Could not parse h/angle from filename.")
                continue
            if ang_i not in full_by_angle:
                print(f"   ⚠️ No full reference for angle={ang_i}. Skipping.")
                continue

            ref_full_path = full_by_angle[ang_i][1]
            print(f"   🧩 Comparing FULL: '{ref_full_path.name}'  ↔  INTERFACE: '{f_int.name}'")

            try:
                data_full = load_pickle(ref_full_path)
                data_int = load_pickle(f_int)
            except Exception as e:
                print(f"   ❌ Failed to load: {e}")
                continue

            try:
                centers = get_coordinate_field(data_full, keys["coord_keys"])
                field_full = data_full[keys["field_key"]]
                field_int = data_int[keys["field_key"]]
            except KeyError as e:
                print(f"   ❌ Missing expected key(s): {e}")
                continue

            x, y = centers[:, 0], centers[:, 1]
            mask = (-0.155 < x) & (x < 0.155) & (-0.155 < y) & (y < 0.155)

            # Compute errors based on error type
            if ERROR_TYPE.lower() == "l1":
                abs_err_field, _, _ = compute_error_fields(field_full, field_int, 1)
                err_value = np.mean(abs_err_field[mask])
                field_to_plot = abs_err_field
                label = f"|{latex_label}|"
            elif ERROR_TYPE.lower() == "l2":
                abs_err_field, _, _ = compute_error_fields(field_full, field_int, 2)
                err_value = np.sqrt(np.mean(abs_err_field[mask]**2))
                field_to_plot = abs_err_field
                label = f"|{latex_label}|"
            elif ERROR_TYPE.lower() == "rell1":
                abs_err_field, full_mag_field, rel_err_field = compute_error_fields(field_full, field_int, 1)
                err_value = np.mean(abs_err_field[mask]) / (np.mean(full_mag_field[mask]) + EPS)
                field_to_plot = rel_err_field
                label = f"|{latex_label}| / |{latex_label}_{{ref}}|"
            elif ERROR_TYPE.lower() == "rell2":
                abs_err_field, full_mag_field, rel_err_field = compute_error_fields(field_full, field_int, 2)
                err_value = np.sqrt(np.sum(abs_err_field[mask]**2) / (np.sum(full_mag_field[mask]**2) + EPS))
                field_to_plot = rel_err_field
                label = f"|{latex_label}| / |{latex_label}_{{ref}}|"
            else:
                raise ValueError(f"Unknown ERROR_TYPE '{ERROR_TYPE}'")

            print(f"   ✅ Mean {ERROR_TYPE} error = {err_value:.3e}")

            h_values.append(h_i)
            mean_errors.append(err_value)

            quantity_label = quantity.replace("_", " ").capitalize()

            pc = plot_error_field(
                centers, field_to_plot, h_i, ang_i, quantity_label, label,
                vmin=global_vmin, vmax=global_vmax
            )

            out_plot = error_out_dir / f"{quantity}_{ERROR_TYPE}_logfield_h{h_i:.3f}_angle_{ang_i:.1f}.pdf"
            plt.savefig(out_plot, format='pdf', bbox_inches="tight")
            print(f"   💾 Saved log error field: {out_plot}")

            if SHOW_PLOTS:
                plt.show()
            else:
                plt.close()

        # Create colorbar with limited number of ticks
        if len(all_field_values) > 0:
            fig, ax = plt.subplots(figsize=(2.5, 6))
            fig.subplots_adjust(left=0.4, right=0.6, top=0.95, bottom=0.05)
            norm = plt.Normalize(vmin=global_vmin, vmax=global_vmax)
            cb = plt.colorbar(
                plt.cm.ScalarMappable(norm=norm, cmap="plasma"),
                cax=ax, orientation="vertical"
            )
            # Add units to colorbar label - rotate and position above with padding, centered
            cb.set_label(r"$\log_{10}$(" + label + ") " + quantity_unit, fontsize=14, 
                        rotation=0, labelpad=10, y=1.06, ha='right')
            
            # Limit colorbar ticks to 5
            ticks = np.linspace(global_vmin, global_vmax, 5)
            cb.set_ticks(ticks)
            cb.ax.tick_params(labelsize=12)
            
            out_cbar = error_out_dir / f"{quantity}_{ERROR_TYPE}_colorbar.pdf"
            plt.savefig(out_cbar, format='pdf', bbox_inches="tight")
            plt.close(fig)
            print(f"   💾 Saved colorbar: {out_cbar}")

        # Plot convergence and pickle data
        if h_values:
            h_values, mean_errors = np.array(h_values), np.array(mean_errors)
            order = np.argsort(h_values)
            plot_convergence(h_values[order], mean_errors[order], latex_label, 
                           quantity_unit, ERROR_TYPE, error_out_dir)

print("\n" + "="*60)
print("✅ Finished comparing all quantities for all error metrics.")
print("="*60)
