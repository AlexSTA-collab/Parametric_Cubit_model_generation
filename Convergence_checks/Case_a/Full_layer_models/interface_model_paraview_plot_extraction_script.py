#!/usr/bin/env python3
"""
extract_parametric_curves.py

This script extracts displacement/reaction/force/stress data from ParaView .case files,
computes derived parameters, updates a pickled dictionary, and saves plots.

It replaces the papermill-based notebook with a command-line interface.
"""

import argparse
from pathlib import Path
import numpy as np
import pickle
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from paraview.simple import *
from paraview import servermanager
from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkTable
from vtk.util.numpy_support import vtk_to_numpy
from pathlib import Path

# ---------- helper functions ----------
def extract_with_selector(src, selector):
    ext = ExtractBlock(Input=src)
    ext.Selectors = [selector]
    UpdatePipeline(proxy=ext)
    return ext

def first_table_from_proxy(pxy):
    fetched = servermanager.Fetch(pxy)
    if isinstance(fetched, vtkTable):
        return fetched
    if isinstance(fetched, vtkMultiBlockDataSet):
        for i in range(fetched.GetNumberOfBlocks()):
            blk = fetched.GetBlock(i)
            if isinstance(blk, vtkTable):
                return blk
            if isinstance(blk, vtkMultiBlockDataSet):
                for j in range(blk.GetNumberOfBlocks()):
                    sub = blk.GetBlock(j)
                    if isinstance(sub, vtkTable):
                        return sub
    raise RuntimeError("No vtkTable found inside PlotSelectionOverTime output.")

def table_to_numpy_dict(tbl):
    out = {}
    for i in range(tbl.GetNumberOfColumns()):
        out[tbl.GetColumnName(i)] = vtk_to_numpy(tbl.GetColumn(i))
    return out

def _norm(s): return "".join(s.lower().split())
def pick_col(columns, *tokens):
    want = [_norm(t) for t in tokens]
    for name in columns:
        n = _norm(name).replace("(block=", "(block=").replace(")(block=", ") (block=")
        if all(w in n for w in want):
            return name
    return None

# ---------- main function ----------
def main(args):
    out_dir = Path(args.out_dir)
    print(out_dir)
    out_prefix = args.out_prefix
    work_dir = Path(args.work_dir)
    case_path = args.case_path

    if not case_path:
        candidates = sorted(work_dir.glob("*.case"), key=lambda p: p.stat().st_mtime)
        case_path = str(candidates[-1]) if candidates else ""
    print("case_path:", case_path)

    # --- constants ---
    TOP_SELECTOR = "/Root/topbody"
    IF_SELECTOR = "/Root/interfacebody"
    TOP_POINT_ID = 120
    IF_CELL_ID = 55

    # Resolve working directory
    work_dir = Path(args.work_dir)

    # --- open sources ---
    top_case_src = work_dir / "Cohesive_zone_model_top.case"
    interface_case_src = work_dir / "Cohesive_zone_model_interface.case"

    # Optionally check which files exist
    if not top_case_src.exists():
        raise FileNotFoundError(f"Top case not found: {top_case_src}")
    if not interface_case_src.exists():
        raise FileNotFoundError(f"Interface case not found: {interface_case_src}")

    top_src = OpenDataFile(str(top_case_src))
    interface_src = OpenDataFile(str(interface_case_src))
    UpdatePipeline(proxy=top_src)
    UpdatePipeline(proxy=interface_src)

    # --- extract ---
    top_blk = extract_with_selector(top_src, TOP_SELECTOR)
    if_blk = extract_with_selector(interface_src, IF_SELECTOR)

    # --- selections ---
    sel_top_pt = IDSelectionSource()
    sel_top_pt.FieldType = "POINT"
    sel_top_pt.IDs = [0, TOP_POINT_ID]

    sel_if_ce = IDSelectionSource()
    sel_if_ce.FieldType = "CELL"
    sel_if_ce.IDs = [0, IF_CELL_ID]

    # --- plot selections ---
    plot_top = PlotSelectionOverTime(Input=top_blk, Selection=sel_top_pt)
    plot_if = PlotSelectionOverTime(Input=if_blk, Selection=sel_if_ce)
    UpdatePipeline(proxy=plot_top)
    UpdatePipeline(proxy=plot_if)

    # --- fetch data ---
    top_tbl = table_to_numpy_dict(first_table_from_proxy(plot_top))
    if_tbl = table_to_numpy_dict(first_table_from_proxy(plot_if))

    # --- pick columns robustly ---
    time_name = pick_col(top_tbl.keys(), "time") or "Time"
    disp_name = pick_col(top_tbl.keys(), "displacement_top", "0")
    react_name = pick_col(top_tbl.keys(), "reaction_top", "0")
    stress_name = pick_col(if_tbl.keys(), "surface_stress_interface", "magnitude")

    missing = [(lbl, nm) for lbl, nm in [
        ("time", time_name),
        ("displacement_top", disp_name),
        ("reaction_top", react_name),
        ("stress_interface", stress_name),
    ] if nm is None]
    if missing:
        print("Available TOP columns:\n  " + "\n  ".join(sorted(top_tbl.keys())))
        print("\nAvailable IF columns:\n  " + "\n  ".join(sorted(if_tbl.keys())))
        raise KeyError("Could not resolve columns: " + ", ".join(f"{lbl}" for lbl, _ in missing))

    # --- numpy arrays ---
    time = np.asarray(top_tbl[time_name], dtype=float)
    displacement_top_mag = np.asarray(top_tbl[disp_name], dtype=float)
    reaction_top_mag = np.abs(np.asarray(top_tbl[react_name], dtype=float))
    stress_interface_mag = np.asarray(if_tbl[stress_name], dtype=float)

    print("OK:")
    print(" time:", time.shape)
    print(" top: displacement_mag:", displacement_top_mag.shape)
    print(" top: reaction_mag:", reaction_top_mag.shape)
    print(" if : stress_mag:", stress_interface_mag.shape)

    # --- compute effective parameters ---
    print(f"E_M={args.E_M}, E_I={args.E_I}, E_0={args.E_0}")
    print("denominator1 =", 2.0 / args.E_0 - 1.0 / args.E_M - 1.0 / args.E_I)
    print("denominator2 =", args.E_M + args.E_I - 2.0 * args.E_0)
    u_max = np.max(displacement_top_mag)
    E_u_eff = (2.0 / args.E_0 - 1.0 / args.E_M - 1.0 / args.E_I) ** (-1)
    E_s_eff = (args.E_M + args.E_I - 2.0 * args.E_0)
    a = f"{args.h * E_u_eff / E_s_eff:.6f}"

    # --- update pickle ---
    out_file = out_dir / "Interface_Model_parametric_curves_Elasticity.pkl"
    if out_file.exists():
        with out_file.open("rb") as f:
            parametric_curves_elasticity = pickle.load(f)
    else:
        parametric_curves_elasticity = {}
    data_entry = [displacement_top_mag, stress_interface_mag]
    parametric_curves_elasticity[a] = data_entry
    with out_file.open("wb") as f:
        pickle.dump(parametric_curves_elasticity, f)

    # --- plotting ---
    plt.rcParams.update({
        "text.usetex": True,
        "font.family": "serif",
        "axes.labelsize": 22,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
    })

    # 1st figure
    out_fig1 = out_dir / "Reaction_displacement"
    out_fig1.mkdir(parents=True, exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(8, 5))
    color = "tab:blue"
    # Force scientific notation with factor shown at top
    ax1.set_xlabel(r"$t$ [days]")
    ax1.set_ylabel(r"$\big|F_x\big|$ [N]", color=color)
    ax1.plot(time, reaction_top_mag, color=color, label=r"$\\||F_x\\||$ [N]")
    ax1.tick_params(axis="y", labelcolor=color, direction="in")
    ax1.tick_params(axis="x", direction="in")
    ax1.yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
    ax1.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    ax1.yaxis.get_offset_text().set_position((0, 1.02))  # x=0, y just above top ticks
    ax1.yaxis.get_offset_text().set_fontsize(12)

    # Limit number of ticks
    ax1.yaxis.set_major_locator(ticker.MaxNLocator(nbins=5))
    ax1.xaxis.set_major_locator(ticker.MaxNLocator(nbins=6))

    # Right y-axis: displacement
    ax2 = ax1.twinx()
    color = "tab:red"
    ax2.set_ylabel(r"$\delta_x$ [mm]", color=color)
    ax2.plot(time, displacement_top_mag, color=color, label=r"$u_x [mm]$")
    ax2.tick_params(axis="y", labelcolor=color, direction="in")

    ax2.yaxis.set_major_locator(ticker.MaxNLocator(nbins=5))

    # Force scientific notation (right y-axis)
    ax2.yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
    ax2.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    ax2.yaxis.get_offset_text().set_position((1, 1.02))  # x=1 so it doesn’t overlap
    ax2.yaxis.get_offset_text().set_fontsize(12)
    ax2.plot(time, displacement_top_mag, color=color)
    fig.tight_layout()
    fig.savefig(out_fig1 / f"{out_prefix}.pdf", bbox_inches="tight")
    plt.close(fig)


    # 2nd figure
    out_fig2 = out_dir / "surface_stress_interface"
    out_fig2.mkdir(parents=True, exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(8, 5))

    # Right y-axis: displacement
    color = "tab:red"
    ax1.set_ylabel(r"$\|\sigma^s_{ij}\|$ [MPa]", color=color)
    ax1.plot(time, stress_interface_mag, color=color, label=r"$t [days]$")
    ax1.tick_params(axis="y", labelcolor=color, direction="in")

    ax2.yaxis.set_major_locator(ticker.MaxNLocator(nbins=5))

    # Force scientific notation (right y-axis)
    ax1.yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
    ax1.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    ax1.yaxis.get_offset_text().set_position((1, 1.02))  # x=1 so it doesn’t overlap
    ax1.yaxis.get_offset_text().set_fontsize(12)
    fig.tight_layout()
    fig.savefig(out_fig2 / f"{out_prefix}.pdf", bbox_inches="tight")
    plt.close(fig)

    # --- after plotting ---
    from interface_model_stress_tools import compute_traction_jump
    from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridWriter

    print("\n=== Computing surface divergence of interface stress ===")
    try:
        # Compute and fetch enriched dataset
        vtk_data = compute_traction_jump(if_blk, surface_stress_name="surface_stress_interface")

        # Write directly using VTK
        writer = vtkXMLUnstructuredGridWriter()
        writer.SetFileName(str(out_dir / f"{out_prefix}_traction_jump.vtu"))
        writer.SetInputData(vtk_data)
        writer.SetDataModeToBinary()  # or SetDataModeToAppended() for XML text
        writer.Write()

        print(f"✅ Saved: {out_prefix}_traction_jump.vtu")

    except Exception as e:
        print("❌ Surface divergence computation failed:", e)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract and plot parametric curves from ParaView output")
    parser.add_argument("--E_M", type=float, required=True)
    parser.add_argument("--E_I", type=float, required=True)
    parser.add_argument("--E_0", type=float, required=True)
    parser.add_argument("--h", type=float, required=True)
    parser.add_argument("--out_dir", type=str, required=True)
    parser.add_argument("--out_prefix", type=str, required=True)
    parser.add_argument("--work_dir", type=str, required=True)
    parser.add_argument("--case_path", type=str, default="")
    args = parser.parse_args()
    main(args)

