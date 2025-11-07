import os
import cubit
import math
from collections import defaultdict
import sys

def centroid(surf_id):
    return cubit.get_surface_centroid(surf_id)

def normal(surf_id):
    return cubit.get_surface_normal(surf_id)

def exterior_surfaces(vol_id):
    surfs = cubit.parse_cubit_list("surface", f"in volume {vol_id}")
    return [s for s in surfs if cubit.parse_cubit_list("volume", f"in surface {s}") == [vol_id]]

def exterior_surfaces2(vol_id):
    return cubit.parse_cubit_list("surface", f"in volume {vol_id}")

def surface_normal(s): 
    return cubit.get_surface_normal(s)

def orient_tag(s):
    nx, ny, nz = map(abs, surface_normal(s))
    if nx > ny and nx > nz:
        return 'X+' if surface_normal(s)[0] > 0 else 'X-'
    elif ny > nx and ny > nz:
        return 'Y+' if surface_normal(s)[1] > 0 else 'Y-'
    else:
        return 'Z+' if surface_normal(s)[2] > 0 else 'Z-'

def generate_cubit_model(cut_angle, height_of_interphase_layer, output_dir="."):
    brick_dims = (1.0, 1.0, 2.0)
    gap = height_of_interphase_layer

    os.makedirs(output_dir, exist_ok=True)

    cubit.init(['cubit'])
    cubit.cmd("reset")

    # -------------------------------------------------
    # 1. Base brick
    # -------------------------------------------------
    cubit.cmd(f"brick x {brick_dims[0]} y {brick_dims[1]} z {brick_dims[2]}")
    v_brick = cubit.get_last_id("volume")

    # -------------------------------------------------
    # 2. Cutting sheet
    # -------------------------------------------------
    cubit.cmd(f"create planar surface with plane zplane offset 0 intersecting volume {v_brick} extended percentage 50")
    sheet_body = cubit.get_last_id("body")
    cubit.cmd(f"rotate volume {sheet_body} angle {cut_angle} about y include_merged")

    # -------------------------------------------------
    # 3. Webcut + cleanup
    # -------------------------------------------------
    cubit.cmd(f"webcut volume {v_brick} with sheet body {sheet_body}")
    cubit.cmd(f"delete volume {sheet_body}")

    vols = cubit.get_entities("volume")
    if len(vols) != 2:
        raise RuntimeError(f"Expected 2 volumes after webcut, got {len(vols)}")

    # -------------------------------------------------
    # 4. Identify top & bottom volumes
    # -------------------------------------------------
    v1, v2 = vols
    z1 = cubit.get_center_point("volume", v1)[2]
    z2 = cubit.get_center_point("volume", v2)[2]
    top_vol, bottom_vol = (v1, v2) if z1 > z2 else (v2, v1)

    # -------------------------------------------------
    # 5. Find the two interface faces
    # -------------------------------------------------
    surf_bot = cubit.parse_cubit_list("surface", f"in volume {bottom_vol}")
    surf_top = cubit.parse_cubit_list("surface", f"in volume {top_vol}")

    best_pair, best_score = None, 1e30
    max_distance = 2 * gap

    for s1 in surf_bot:
        c1, n1 = centroid(s1), normal(s1)
        for s2 in surf_top:
            c2, n2 = centroid(s2), normal(s2)
            dist = math.dist(c1, c2)
            dot = abs(sum(a*b for a, b in zip(n1, n2)))
            score = dist + 10.0 * dot
            if dist < max_distance and score < best_score:
                best_score = score
                best_pair = (s1, s2)

    if best_pair is None:
        raise RuntimeError("Could not find suitable interface surface pair. Check gap or cut geometry.")

    s_bot, s_top = best_pair
    print(f"Selected interface surfaces: bottom {s_bot}, top {s_top}")

    # -------------------------------------------------
    # 6. Exterior (non-interface) faces
    # -------------------------------------------------
    interface_set = {s_bot, s_top}
    ext_surfs_bot = exterior_surfaces(bottom_vol)
    ext_surfs_top = exterior_surfaces(top_vol)

    # -------------------------------------------------
    # 7. Move top body and create loft volume (scaling workaround)
    # -------------------------------------------------
    print("Creating cohesive layer with scaling workaround...")

    model_size = max(brick_dims)
    scale_factor = max(1.0, 10.0 * model_size / gap)  # adaptive scale based on gap
    print(f"Scaling volumes by factor {scale_factor:.3e} for robust loft creation")

    # --- Scale up only the original volumes (correct syntax!) ---
    cubit.cmd(f"Volume {bottom_vol} Scale {scale_factor} About 0 0 0")
    cubit.cmd(f"Volume {top_vol} Scale {scale_factor} About 0 0 0")

    # Move the top volume upward in the scaled space
    cubit.cmd(f"move volume {top_vol} x 0 y 0 z {gap * scale_factor} include_merged")

    # Create the cohesive (lofted) volume between the two scaled surfaces
    cubit.cmd(f"create volume loft surface {s_bot},{s_top}")
    v_cohesive = cubit.get_last_id("volume")

    # --- Scale all three volumes back to original size ---
    cubit.cmd(f"Volume {bottom_vol} Scale {1.0 / scale_factor} About 0 0 0")
    cubit.cmd(f"Volume {top_vol} Scale {1.0 / scale_factor} About 0 0 0")
    cubit.cmd(f"Volume {v_cohesive} Scale {1.0 / scale_factor} About 0 0 0")

    print(f"Scaled back to original model size (factor {1/scale_factor:.3e})")

    # Perform imprint/merge after returning to correct scale
    cubit.cmd("imprint all")
    cubit.cmd("merge all")

    # Debug info: show volumes and their surfaces
    for v in cubit.get_entities("volume"):
        surfs = cubit.parse_cubit_list("surface", f"in volume {v}")
        print(f"Volume {v} has {len(surfs)} surfaces: {tuple(surfs)}")


    
    # -------------------------------------------------
    # 8. Curve classification helpers (robust post-merge)
    # -------------------------------------------------
    def curve_direction(curve_id):
        """Estimate direction vector from bounding box (robust even after merge)."""
        try:
            xmin, ymin, zmin, xmax, ymax, zmax = cubit.get_bounding_box("curve", curve_id)
        except:
            return (0.0, 0.0, 0.0)
        return (xmax - xmin, ymax - ymin, zmax - zmin)

    def is_vertical(curve_id, tol=1e-6):
        """Detect if curve extends primarily along Z."""
        dx, dy, dz = curve_direction(curve_id)
        if dx == dy == dz == 0.0:
            return False
        return abs(dz) > abs(dx) and abs(dz) > abs(dy) + tol

    # -------------------------------------------------
    # 9. Automatic curve seeding and cohesive curve detection
    # -------------------------------------------------
    print("Identifying curve groups and setting meshing parameters...")

    # --- classify top and bottom surface curves ---
    curves_top = cubit.parse_cubit_list("curve", f"in surface {s_top}")
    curves_bot = cubit.parse_cubit_list("curve", f"in surface {s_bot}")

    horiz_top = [c for c in curves_top if not is_vertical(c)]
    vert_top  = [c for c in curves_top if is_vertical(c)]
    horiz_bot = [c for c in curves_bot if not is_vertical(c)]
    vert_bot  = [c for c in curves_bot if is_vertical(c)]

    print(f"Top surface: horizontal {horiz_top}, vertical {vert_top}")
    print(f"Bottom surface: horizontal {horiz_bot}, vertical {vert_bot}")

    # --- apply seeding rules ---
    
    bias_factor = (4.+math.log10(gap)*0.8)/5.
    inverse_bias_factor = 5./ (4.+math.log10(gap)*0.8)
    for c in horiz_top:
        cubit.cmd(f"curve {c} interval 10")
    
    vertical_interval = int(-math.log10(gap)*1.)
    for c in vert_top:
        cubit.cmd(f"curve {c} interval {vertical_interval}")
        cubit.cmd(f"curve {c} scheme bias factor {bias_factor}")

    for c in horiz_bot:
        cubit.cmd(f"curve {c} interval 10")
    for c in vert_bot:
        cubit.cmd(f"curve {c} interval {vertical_interval}")
        cubit.cmd(f"curve {c} scheme bias factor {inverse_bias_factor}")

    # --- cohesive layer curves (non-interface) ---
    curves_coh = cubit.parse_cubit_list("curve", f"in volume {v_cohesive}")
    print("Curves COH:",curves_coh)
    excluded = set(curves_top + curves_bot)
    print(("Curves COH Excluded:",excluded))
    coh_vert = [c for c in curves_coh if c not in excluded]
    print(f"Cohesive vertical curves (non-interface): {coh_vert}")

    for c in coh_vert:
        cubit.cmd(f"curve {c} interval 1")
        cubit.cmd(f"curve {c} scheme equal")

    # -------------------------------------------------
    # 9. Mesh generation with refinement
    # -------------------------------------------------
    print("Meshing volumes and refining interface-adjacent surfaces...")

    cubit.cmd(f"mesh volume {bottom_vol}")
    cubit.cmd(f"mesh volume {top_vol}")
    numsplit = int(-math.log10(gap))
    cubit.cmd(f"refine surface {s_top} numsplit {numsplit} bias 16 depth 0.5")#numsplit 1 bias 1 depth 1")
    cubit.cmd(f"refine surface {s_bot} numsplit {numsplit} bias 16 depth 0.5")

    cubit.cmd(f"volume {v_cohesive} size {gap}")
    cubit.cmd(f"mesh volume {v_cohesive}")
    
    print("✅ Meshing and cohesive-layer refinement completed successfully.")

    
    # -------------------------------------------------
    # 10. Recompute exterior faces
    # -------------------------------------------------
    ext_surfs_bot = exterior_surfaces2(bottom_vol)
    ext_surfs_top = exterior_surfaces2(top_vol)

    # -------------------------------------------------
    # 11. Node sets for outer faces (excluding interface)
    # -------------------------------------------------
    surf_map = defaultdict(list)
    for vol, label, faces in [(bottom_vol, "bottom", ext_surfs_bot), (top_vol, "top", ext_surfs_top)]:
        for s in faces:
            surf_map[f"{label}-{orient_tag(s)}"].append(s)

    ns_id = 1
    nodesets = {}
    for name, faces in surf_map.items():
        for s in faces:
            cubit.cmd(f"nodeset {ns_id} add node in surface {s}")
        cubit.cmd(f'nodeset {ns_id} name "{name}"')
        nodesets[name] = ns_id
        print(f"Nodeset {ns_id}: {name} -> faces {faces}")
        ns_id += 1

    # -------------------------------------------------
    # 12. Export include files
    # -------------------------------------------------
    all_nodes = cubit.get_entities("node")
    node_coords = {nid: cubit.get_nodal_coordinates(nid) for nid in all_nodes}
    with open(os.path.join(output_dir, "include_nodes.inp"), "w") as f:
        for nid in sorted(node_coords):
            x, y, z = node_coords[nid]
            f.write(f"{nid}, {x}, {y}, {z}\n")

    vol_region_map = {"bottom": bottom_vol, "interface": v_cohesive, "top": top_vol}
    element_sets = {}
    for name, vid in vol_region_map.items():
        elems = cubit.parse_cubit_list("hex", f"in volume {vid}")
        element_sets[name] = {}
        for eid in elems:
            conn = cubit.get_connectivity("hex", eid)
            if isinstance(conn, int):
                conn = [conn]
            element_sets[name][eid] = conn

    for name, elems in element_sets.items():
        with open(os.path.join(output_dir, f"include_elset_{name}.inp"), "w") as f:
            for eid, conn in sorted(elems.items()):
                if isinstance(conn, int):
                    conn = [conn]
                f.write(f"{eid}, {', '.join(map(str, conn))}\n")

    nodeset_data = {}
    for name, nsid in nodesets.items():
        node_ids = cubit.parse_cubit_list("node", f"in nodeset {nsid}")
        if isinstance(node_ids, int):
            node_ids = [node_ids]
        nodeset_data[name] = node_ids
        print(f"Nodeset '{name}' has {len(node_ids)} nodes")

    for name, node_ids in nodeset_data.items():
        fname = os.path.join(output_dir, f"include_nset_{name}.inp")
        with open(fname, "w") as f:
            for i, nid in enumerate(sorted(node_ids), 1):
                f.write(f"{nid}, " if i % 8 else f"{nid}\n")
            if i % 8:
                f.write("\n")

    print("Mesh include files written:")
    print("  - include_nodes.inp")
    print("  - include_elset_{bottom, interface, top}.inp")
    print("  - include_nset_<name>.inp")

if __name__ == "__main__":
    angle = float(sys.argv[1])
    height_of_interphase_layer = float(sys.argv[2]) 
    generate_cubit_model(angle, height_of_interphase_layer)

