#!/usr/bin/env python3
"""
Extract displacement / force / stress curves from ParaView case files
and store them in a pickle using tuple keys (a, b, c).

Pickle format:
    parametric_curves_creep[(a, b, c)] = {
        "displacement": np.ndarray,
        "force": np.ndarray,
        "stress": np.ndarray,
    }

Notes:
- No plotting.
- No backward compatibility.
- --out_prefix is accepted for workflow compatibility (ignored).
"""

import argparse
from pathlib import Path
import numpy as np
import pickle
from paraview.simple import *
from paraview import servermanager
from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkTable
from vtk.util.numpy_support import vtk_to_numpy


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------
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
    raise RuntimeError("No vtkTable found.")


def table_to_numpy_dict(tbl):
    return {
        tbl.GetColumnName(i): vtk_to_numpy(tbl.GetColumn(i))
        for i in range(tbl.GetNumberOfColumns())
    }


def _norm(s):
    return "".join(s.lower().split())


def pick_col(columns, *tokens):
    want = [_norm(t) for t in tokens]
    for name in columns:
        if all(w in _norm(name) for w in want):
            return name
    return None


def find_point_id_at_coordinate(src, target_coord):
    data = servermanager.Fetch(src)
    if isinstance(data, vtkMultiBlockDataSet):
        for i in range(data.GetNumberOfBlocks()):
            blk = data.GetBlock(i)
            if blk and blk.GetNumberOfPoints() > 0:
                data = blk
                break

    pts = data.GetPoints()
    target = np.array(target_coord)

    dmin, pid_min = float("inf"), -1
    for pid in range(pts.GetNumberOfPoints()):
        d = np.linalg.norm(np.array(pts.GetPoint(pid)) - target)
        if d < dmin:
            dmin, pid_min = d, pid
    return pid_min


def find_cell_id_at_coordinate(src, target_coord):
    data = servermanager.Fetch(src)
    if isinstance(data, vtkMultiBlockDataSet):
        for i in range(data.GetNumberOfBlocks()):
            blk = data.GetBlock(i)
            if blk and blk.GetNumberOfCells() > 0:
                data = blk
                break

    target = np.array(target_coord)
    dmin, cid_min = float("inf"), -1

    for cid in range(data.GetNumberOfCells()):
        cell = data.GetCell(cid)
        bounds = [0.0] * 6
        cell.GetBounds(bounds)
        center = np.array([
            0.5 * (bounds[0] + bounds[1]),
            0.5 * (bounds[2] + bounds[3]),
            0.5 * (bounds[4] + bounds[5]),
        ])
        d = np.linalg.norm(center - target)
        if d < dmin:
            dmin, cid_min = d, cid
    return cid_min


# ---------------------------------------------------------------------
def main(args):
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    h_str = f"{args.h:g}"
    top_case = f"./Cohesive_zone_model_top_{h_str}.case"
    interface_case = f"./Cohesive_zone_model_interface_{h_str}.case"

    top_src = OpenDataFile(top_case)
    if_src = OpenDataFile(interface_case)
    UpdatePipeline(proxy=top_src)
    UpdatePipeline(proxy=if_src)

    top_blk = extract_with_selector(top_src, "/Root/topbody")
    if_blk = extract_with_selector(if_src, "/Root/interfacebody")

    top_pid = find_point_id_at_coordinate(
        top_blk, (0.0, 0.0, 1.0 + args.h)
    )
    if_cid = find_cell_id_at_coordinate(
        if_blk, (-args.h / 4.0, -args.h / 4.0, args.h / 2.0)
    )

    sel_top = IDSelectionSource(FieldType="POINT", IDs=[0, top_pid])
    sel_if = IDSelectionSource(FieldType="CELL", IDs=[0, if_cid])

    plot_top = PlotSelectionOverTime(Input=top_blk, Selection=sel_top)
    plot_if = PlotSelectionOverTime(Input=if_blk, Selection=sel_if)
    UpdatePipeline(proxy=plot_top)
    UpdatePipeline(proxy=plot_if)

    top_tbl = table_to_numpy_dict(first_table_from_proxy(plot_top))
    if_tbl = table_to_numpy_dict(first_table_from_proxy(plot_if))
    
    time_col   = pick_col(top_tbl, "time")
    disp_col   = pick_col(top_tbl, "displacement")
    force_col  = pick_col(if_tbl, "force")
    stress_col = pick_col(if_tbl, "stress")
    
    time = np.asarray(top_tbl[time_col], dtype=float)
    displacement = np.asarray(top_tbl[disp_col], dtype=float)
    force        = np.asarray(if_tbl[force_col], dtype=float)
    stress       = np.asarray(if_tbl[stress_col], dtype=float)

    Dt = 0.05
    Dt_m = Dt / args.m_Ju
    beta = np.exp(-Dt_m)
    lambda1 = (1.0 - beta) / Dt_m
    E_eff = (args.E_0 + lambda1 * args.n_Ju) / (args.E_M + args.E_I)

    key = (float(E_eff), float(args.m_Ju), float(args.h))

    out_file = out_dir / "parametric_curves_creep.pkl"
    data = {} if not out_file.exists() else pickle.load(open(out_file, "rb"))

    data[key] = {
        "time": time,
        "displacement": displacement,
        "force": force,
        "stress": stress,
    }

    pickle.dump(data, open(out_file, "wb"))
    print(f"✓ stored curve for key={key}")


# ---------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--E_M", type=float, required=True)
    parser.add_argument("--E_I", type=float, required=True)
    parser.add_argument("--E_0", type=float, required=True)
    parser.add_argument("--h", type=float, required=True)
    parser.add_argument("--m_Ju", type=float, required=True)
    parser.add_argument("--n_Ju", type=float, required=True)

    parser.add_argument("--out_dir", type=str, required=True)
    parser.add_argument("--work_dir", type=str, required=True)

    main(parser.parse_args())
