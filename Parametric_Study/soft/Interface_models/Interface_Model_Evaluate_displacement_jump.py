import numpy as np
import pickle
import matplotlib.pyplot as plt
from paraview.simple import *



# -------------------------------------------------------
# Visualization helper
# -------------------------------------------------------
def plot_displacement_jump(points_bottom, displacement_jump, layer_height, angle_deg):
    """Plot traction jump magnitude on structured grid or scatter plot."""
    tol = 1e-6
    displacement_jump_magnitude = np.linalg.norm(displacement_jump, axis=1)

    x_coords = points_bottom[:, 0]
    y_coords = points_bottom[:, 1]
    x_unique = np.unique(np.round(x_coords / tol) * tol)
    y_unique = np.unique(np.round(y_coords / tol) * tol)
    nx, ny = len(x_unique), len(y_unique)

    print(f"Grid dimensions: {ny} x {nx} = {ny * nx}")
    print(f"Jump values: {len(displacement_jump_magnitude)}")

    plt.figure(figsize=(10, 8))

    if ny * nx == len(displacement_jump_magnitude):
        print("Data forms a complete structured grid")

        Z = np.full((ny, nx), np.nan)
        for i in range(len(x_coords)):
            x_idx = np.where(x_unique == np.round(x_coords[i] / tol) * tol)[0][0]
            y_idx = np.where(y_unique == np.round(y_coords[i] / tol) * tol)[0][0]
            Z[y_idx, x_idx] = displacement_jump_magnitude[i]

        X, Y = np.meshgrid(x_unique, y_unique)
        pc = plt.pcolormesh(X, Y, Z, shading="auto", cmap="viridis")
        plt.colorbar(pc, label="Displacement Jump Magnitude")
        plt.title(f"Displacement Jump (h={layer_height}, angle={angle_deg}°)")
    else:
        print("Data does not form a complete structured grid - using scatter plot instead")
        scatter = plt.scatter(
            x_coords, y_coords,
            c=displacement_jump_magnitude,
            cmap="viridis", s=50, alpha=0.8
        )
        plt.colorbar(scatter, label="Displacement Jump Magnitude")
        plt.title(f"Displacement Jump (Scatter) (h={layer_height}, angle={angle_deg}°)")

    plt.xlabel("x")
    plt.ylabel("y")
    plt.axis("equal")
    plt.tight_layout()
    plt.show()


def compute_and_save_displacement_jump(
    casefile_bottom: str,
    casefile_top: str,
    layer_height: float,
    angle_deg: float,
    output_dir: str = ".",
    plot: bool = False):
    """
    Computes the displacement jump between two EnSight surfaces (bottom/top),
    aligns them spatially, and saves the sorted points and displacement jump to a pickle file.

    Parameters
    ----------
    casefile_bottom : str
        Path to the bottom EnSight case file (.case)
    casefile_top : str
        Path to the top EnSight case file (.case)
    layer_height : float
        Height of the layer between bottom and top (used for clipping planes)
    angle_deg : float
        Inclination angle (deg) of the interface around the Y-axis
    output_dir : str, optional
        Directory where to save the pickle file (default: current directory)
    """

    import os
    from vtk.util.numpy_support import vtk_to_numpy

    # --- Construct output filename ---
    output_pkl = os.path.join(
        output_dir,
        f"displacement_jump_h{layer_height:.3f}_angle_{angle_deg:.1f}.pkl"
    )

    # --- Geometry setup ---
    eps = layer_height / 1e3
    normal_vector = np.array([
        np.sin(np.radians(angle_deg)),
        0.0,
        np.cos(np.radians(angle_deg))
    ])
    origin_slice1_bottom = [0.0, 0.0, 0 -eps]
    origin_slice2_top = [0.0, 0.0, layer_height + eps]

    # --- Read EnSight files ---
    ensight_reader_bottom = EnSightReader(
        registrationName="bottom_reader",
        CaseFileName=casefile_bottom,
    )
    ensight_reader_top = EnSightReader(
        registrationName="top_reader",
        CaseFileName=casefile_top,
    )

    UpdatePipeline(proxy=ensight_reader_bottom)
    UpdatePipeline(proxy=ensight_reader_top)

    timesteps = ensight_reader_bottom.TimestepValues
    if not timesteps:
        raise RuntimeError("No timesteps found in EnSight reader")

    last_time = timesteps[-1]
    print(f"Setting both readers to last timestep: {last_time}")

    scene = GetAnimationScene()
    scene.AnimationTime = last_time

    # --- Extract blocks ---
    extractBlock_bottom = ExtractBlock(registrationName="ExtractBottom", Input=ensight_reader_bottom)
    extractBlock_bottom.Selectors = ["/Root/bottombody"]
    extractBlock_bottom.UpdatePipeline()

    extractBlock_top = ExtractBlock(registrationName="ExtractTop", Input=ensight_reader_top)
    extractBlock_top.Selectors = ["/Root/topbody"]
    extractBlock_top.UpdatePipeline()

    # --- Clip bottom ---
    slice_bottom = Slice(registrationName="SliceBottom", Input=extractBlock_bottom)
    slice_bottom.SliceType = "Plane"
    slice_bottom.SliceType.Origin = origin_slice1_bottom
    slice_bottom.SliceType.Normal = (-normal_vector).tolist()
    slice_bottom.UpdatePipeline()

    # --- Clip top ---
    slice_top = Slice(registrationName="SliceTop", Input=extractBlock_top)
    slice_top.SliceType = "Plane"
    slice_top.SliceType.Origin = origin_slice2_top
    slice_top.SliceType.Normal = normal_vector.tolist()
    slice_top.UpdatePipeline()
    
    # --- Advance time to ensure data is up-to-date ---
    for name, proxy in GetSources().items():
        UpdatePipeline(time=last_time, proxy=proxy)
    # --- Fetch data ---
    data_bottom = servermanager.Fetch(slice_bottom).GetBlock(0)
    data_top = servermanager.Fetch(slice_top).GetBlock(0)

    points_bottom = vtk_to_numpy(data_bottom.GetPoints().GetData())
    points_top = vtk_to_numpy(data_top.GetPoints().GetData())
    displacement_bottom = vtk_to_numpy(data_bottom.GetPointData().GetArray("displacement_bottom"))
    displacement_top = vtk_to_numpy(data_top.GetPointData().GetArray("displacement_top"))

    # --- Align by (x, y) ---
    tol = 1e-6
    xy_bottom = np.round(points_bottom[:, :2] / tol) * tol
    xy_top = np.round(points_top[:, :2] / tol) * tol

    idx_bottom = np.lexsort((xy_bottom[:, 1], xy_bottom[:, 0]))
    idx_top = np.lexsort((xy_top[:, 1], xy_top[:, 0]))

    points_bottom_sorted = points_bottom[idx_bottom]
    points_top_sorted = points_top[idx_top]

    if not np.allclose(points_bottom_sorted[:, :2], points_top_sorted[:, :2], atol=tol):
        raise ValueError("XY coordinates between top and bottom surfaces do not align.")

    # --- Compute displacement jump ---
    displacement_jump = displacement_top[idx_top] - displacement_bottom[idx_bottom]
     
    # --- Save only the essentials ---
    to_save = {
        "points_bottom": points_bottom_sorted,
        "points_top": points_top_sorted,
        "displacement_jump": displacement_jump,
    }

    with open(output_pkl, "wb") as f:
        pickle.dump(to_save, f)

    print(f"Saved data to '{output_pkl}'")

    # --- Optional visualization ---
    if plot:
        plot_displacement_jump(points_bottom_sorted, displacement_jump, layer_height, angle_deg)

def main():
    """
    Example standalone usage for quick testing or scripting.
    Modify the file paths and parameters below as needed.
    """
    case_bottom = "/home/alexsta1993/Documents/STATHAS_VIENNA_POSTDOC/Applications_Examples/EdelweisModels/Cohesive_Zone_models/3D/Three_Body_Cubit/Comparizon_LinearElastic/Convergence_check/Case_a/Interface_models/Tested_input_files_case_a_angle_10/Cohesive_zone_model_bottom_h_0.01.case"
    case_top = "/home/alexsta1993/Documents/STATHAS_VIENNA_POSTDOC/Applications_Examples/EdelweisModels/Cohesive_Zone_models/3D/Three_Body_Cubit/Comparizon_LinearElastic/Convergence_check/Case_a/Interface_models/Tested_input_files_case_a_angle_10/Cohesive_zone_model_top_h_0.01.case"
    layer_height = 0.01
    angle_deg = 10
    output_dir = "."
    plot_flag = True  # set to False to skip plotting

    compute_and_save_displacement_jump(
        casefile_bottom=case_bottom,
        casefile_top=case_top,
        layer_height=layer_height,
        angle_deg=angle_deg,
        output_dir=output_dir,
        plot=plot_flag
    )


if __name__ == "__main__":
    main()
