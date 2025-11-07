import argparse
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# -------------- IO helpers --------------

def read_nodeset_file(path: Path) -> List[int]:
    """
    Reads an include_nset_<name>.inp file containing node IDs.
    Handles arbitrary comma/space-separated lists across lines.
    """
    ids: List[int] = []
    if not path.exists():
        return ids
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("**"):
                continue
            # split by comma or whitespace, strip trailing commas
            parts = [p.strip().rstrip(",") for p in re.split(r"[,\s]+", line) if p.strip()]
            for p in parts:
                if p.isdigit() or (p.startswith("-") and p[1:].isdigit()):
                    ids.append(int(p))
    return ids

def read_element_connectivity_file(path: Path) -> Dict[int, List[int]]:
    """
    Reads an include_elset_<region>.inp file containing:
      eid, n1, n2, n3, ...
    Returns dict: eid -> [nids...]
    """
    conn: Dict[int, List[int]] = {}
    if not path.exists():
        return conn
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("**"):
                continue
            # Example line: 123, 4, 5, 6, 7, 8, 9, 10, 11
            parts = [p.strip().rstrip(",") for p in line.split(",")]
            if not parts or not parts[0].lstrip("-").isdigit():
                continue
            eid = int(parts[0])
            nodes = [int(p) for p in parts[1:] if p.lstrip("-").isdigit()]
            conn[eid] = nodes
    return conn

def write_element_connectivity_file(path: Path, conn: Dict[int, List[int]], eids: List[int]):
    """
    Writes lines: eid, n1, n2, ...
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for eid in sorted(eids):
            nodes = conn.get(eid, [])
            f.write(f"{eid}, {', '.join(map(str, nodes))}\n")

# -------------- Core selection --------------

def select_elements_touching_nodeset(
    elem_conn: Dict[int, List[int]],
    nodeset: Set[int],
    mode: str = "any",  # "any" or "all"
) -> List[int]:
    """
    Return element IDs where connectivity intersects nodeset ('any') or is subset of nodeset ('all').
    """
    if mode not in {"any", "all"}:
        raise ValueError("mode must be 'any' or 'all'")
    selected: List[int] = []
    if mode == "any":
        for eid, conn in elem_conn.items():
            if any(n in nodeset for n in conn):
                selected.append(eid)
    else:
        for eid, conn in elem_conn.items():
            if conn and all(n in nodeset for n in conn):
                selected.append(eid)
    return selected

# -------------- Main pipeline --------------

def main():
    ap = argparse.ArgumentParser(description="Postprocess element sets from nodesets using include files.")
    ap.add_argument("output_dir", type=Path, help="Directory containing include files written by your Cubit script.")
    ap.add_argument(
        "--elset-files",
        nargs="+",
        default=["include_elset_bottom.inp", "include_elset_top.inp", "include_elset_interface.inp"],
        help="Element include files to consider (relative to output_dir).",
    )
    ap.add_argument(
        "--mode", choices=["any", "all"], default="any",
        help="Select elements with ANY node in nodeset (default) or ALL nodes in nodeset.",
    )
    ap.add_argument(
        "--only-prefixes",
        nargs="*",
        default=["top", "bottom"],  # set [] to process all nodesets
        help="If given, only process nodesets whose name starts with any of these prefixes.",
    )
    args = ap.parse_args()

    out_dir = args.output_dir

    # 1) Load element connectivity from the provided elset include files
    elem_conn: Dict[int, List[int]] = {}
    for rel in args.elset_files:
        p = out_dir / rel
        part = read_element_connectivity_file(p)
        # merge; later files can override if same eid appears (unlikely if volumes are disjoint)
        elem_conn.update(part)

    if not elem_conn:
        print("No element connectivity found. Check --elset-files and output_dir.")
        return

    # 2) Discover all nodeset include files: include_nset_*.inp
    nset_files = list(out_dir.glob("include_nset_*.inp"))
    if not nset_files:
        print("No nodeset include files found (include_nset_*.inp).")
        return

    # 3) For each nodeset, filter elements and write a new include
    for nfile in nset_files:
        # nodeset name is the stem after 'include_nset_' and before '.inp'
        name = nfile.stem[len("include_nset_"):]
        if args.only_prefixes and not any(name.startswith(pref) for pref in args.only_prefixes):
            continue

        node_ids = set(read_nodeset_file(nfile))
        if not node_ids:
            print(f"[skip] Nodeset '{name}' is empty.")
            continue

        eids = select_elements_touching_nodeset(elem_conn, node_ids, mode=args.mode)
        print(f"Nodeset '{name}': {len(node_ids)} nodes -> {len(eids)} touching elements.")

        out_name = f"include_elset_{name}_elems.inp"
        write_element_connectivity_file(out_dir / out_name, elem_conn, eids)

    print("Done.")

if __name__ == "__main__":
    main()

