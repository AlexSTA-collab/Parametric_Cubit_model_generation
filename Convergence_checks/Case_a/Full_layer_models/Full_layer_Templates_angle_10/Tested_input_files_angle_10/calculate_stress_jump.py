import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def compute_and_store_traction_jump(
    top_file: str,
    bottom_file: str,
    output_dir: str = ".",
    normal: np.ndarray = np.array([0.0, 0.0, 1.0]),
    plot: bool = True,
) -> Path:
    """
    Compute the traction jump between two stress datasets stored in HDF5 files
    (each with Data0=coords, Data1=stresses).

    Parameters
    ----------
    top_file : str
        Path to the HDF5 file containing top region data.
    bottom_file : str
        Path to the HDF5 file containing bottom region data.
    output_dir : str, optional
        Directory where outputs are saved.
    normal : np.ndarray, optional
        Interface normal vector (default [0, 0, 1]).
    plot : bool, optional
        Whether to display a traction-jump magnitude plot.

    Returns
    -------
    Path
        Path to the generated traction_jump.h5 file.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_h5 = output_dir / "traction_jump.h5"
    output_csv = output_dir / "traction_jump.csv"

    # ------------------------------------------------------
    # Load data
    # ------------------------------------------------------
    def load_data(fname):
        with h5py.File(fname, "r") as f:
            coords = np.array(f["Data0"])
            stress = np.array(f["Data1"])
        return coords, stress

    coords_top, stress_top = load_data(top_file)
    coords_bot, stress_bot = load_data(bottom_file)

    # ------------------------------------------------------
    # Match by (x, y)
    # ------------------------------------------------------
    XY_top = np.round(coords_top[:, :2], 8)
    XY_bot = np.round(coords_bot[:, :2], 8)
    bot_lookup = {
        tuple(xy): (stress, z)
        for xy, stress, z in zip(XY_bot, stress_bot, coords_bot[:, 2])
    }

    rows = []
    for xy, s_top, z_top in zip(XY_top, stress_top, coords_top[:, 2]):
        key = tuple(xy)
        if key not in bot_lookup:
            continue
        s_bot, z_bot = bot_lookup[key]
        s_jump = s_top - s_bot

        # stress order: [Sxx, Syy, Szz, Sxy, Syz, Sxz]
        Sxx, Syy, Szz, Sxy, Syz, Sxz = s_jump
        sigma = np.array([[Sxx, Sxy, Sxz],
                          [Sxy, Syy, Syz],
                          [Sxz, Syz, Szz]])
        t_jump = sigma @ normal
        tmag = np.linalg.norm(t_jump)

        rows.append((xy[0], xy[1], z_top, z_bot, *s_jump, *t_jump, tmag))

    cols = [
        "x", "y", "z_top", "z_bot",
        "Sxx_jump", "Syy_jump", "Szz_jump", "Sxy_jump", "Syz_jump", "Sxz_jump",
        "tx_jump", "ty_jump", "tz_jump", "tmag_jump",
    ]
    df = pd.DataFrame(rows, columns=cols)
    print(f"Matched {len(df)} common points")

    # ------------------------------------------------------
    # Save results
    # ------------------------------------------------------
    with h5py.File(output_h5, "w") as f:
        f.create_dataset("Coordinates", data=df[["x", "y", "z_top"]].to_numpy())
        f.create_dataset(
            "StressJump",
            data=df[["Sxx_jump", "Syy_jump", "Szz_jump", "Sxy_jump", "Syz_jump", "Sxz_jump"]].to_numpy(),
        )
        f.create_dataset("TractionJump", data=df[["tx_jump", "ty_jump", "tz_jump"]].to_numpy())
        f.create_dataset("TractionJumpMagnitude", data=df["tmag_jump"].to_numpy())

    df.to_csv(output_csv, index=False)
    print(f"✅ Results stored in: {output_h5}")
    print(f"✅ CSV summary: {output_csv}")

    # ------------------------------------------------------
    # Optional visualization
    # ------------------------------------------------------
    if plot:
        x_unique = np.unique(df["x"])
        y_unique = np.unique(df["y"])
        nx, ny = len(x_unique), len(y_unique)
        df_sorted = df.sort_values(["y", "x"])
        try:
            Z = df_sorted["tmag_jump"].to_numpy().reshape(ny, nx)
            X, Y = np.meshgrid(x_unique, y_unique)
            plt.figure(figsize=(7, 5))
            pc = plt.pcolormesh(X, Y, Z, shading="auto", cmap="viridis")
            plt.colorbar(pc, label="|Traction jump|")
            plt.xlabel("x")
            plt.ylabel("y")
            plt.title("Traction jump magnitude (filled map)")
            plt.axis("equal")
            plt.tight_layout()
            plt.show()
        except ValueError:
            print("⚠️ Could not reshape data to structured grid; skipped plot.")

    return output_h5


# ======================================================
# Main entry point
# ======================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compute traction jump between two HDF5 datasets.")
    parser.add_argument("top_file", help="Path to the top HDF5 file (with Data0, Data1).")
    parser.add_argument("bottom_file", help="Path to the bottom HDF5 file (with Data0, Data1).")
    parser.add_argument("-o", "--output_dir", default="results", help="Output directory (default: results/).")
    parser.add_argument("--no-plot", action="store_true", help="Disable plotting.")
    parser.add_argument("--normal", nargs=3, type=float, default=[0.0, 0.0, 1.0],
                        help="Interface normal vector (default: 0 0 1).")

    args = parser.parse_args()

    compute_and_store_traction_jump(
        top_file=args.top_file,
        bottom_file=args.bottom_file,
        output_dir=args.output_dir,
        normal=np.array(args.normal, dtype=float),
        plot=not args.no_plot,
    )

