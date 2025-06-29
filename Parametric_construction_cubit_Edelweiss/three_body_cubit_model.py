import cubit
import math
from collections import defaultdict

# ---------------- USER PARAMETERS ----------------
brick_dims = (1.0, 1.0, 2.0)        # X, Y, Z
cut_angle  = 0.0                   # degrees (+Y axis)
gap        = 0.02                   # separation after cut (along +Z)
mesh_size  = 0.1                    # global element size
# -------------------------------------------------

cubit.init(['cubit'])
cubit.cmd("reset")

# -------------------------------------------------
# 1. Base brick
# -------------------------------------------------
cubit.cmd(f"brick x {brick_dims[0]} y {brick_dims[1]} z {brick_dims[2]}")
v_brick = cubit.get_last_id("volume")

# -------------------------------------------------
# 2. Cutting sheet: create & rotate
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
# Use Z-coordinate of the volume centroid to decide top vs. bottom
v1, v2 = vols

z1 = cubit.get_center_point("volume", v1)[2]
z2 = cubit.get_center_point("volume", v2)[2]

top_vol, bottom_vol = (v1, v2) if z1 > z2 else (v2, v1)

# -------------------------------------------------
# 5. Find the two interface faces (one on each volume)
# -------------------------------------------------
def centroid(surf_id):
    return cubit.get_surface_centroid(surf_id)

def normal(surf_id):
    return cubit.get_surface_normal(surf_id)

surf_bot = cubit.parse_cubit_list("surface", f"in volume {bottom_vol}")
surf_top = cubit.parse_cubit_list("surface", f"in volume {top_vol}")

best_pair, best_score = None, 1e30
max_distance = 2 * gap  # anything beyond this is too far

print(f"Trying to match {len(surf_bot)} bottom faces to {len(surf_top)} top faces...")

for s1 in surf_bot:
    c1, n1 = centroid(s1), normal(s1)
    for s2 in surf_top:
        c2, n2 = centroid(s2), normal(s2)
        dist = math.dist(c1, c2)
        dot  = abs(sum(a*b for a, b in zip(n1, n2)))
        score = dist + 10.0 * dot
        print(f"  s1={s1}, s2={s2}, dist={dist:.4f}, dot={dot:.4f}, score={score:.4f}")
        if dist < max_distance and score < best_score:
            best_score = score
            best_pair = (s1, s2)

if best_pair is None:
    raise RuntimeError("Could not find suitable interface surface pair. Check gap or cut geometry.")

s_bot, s_top = best_pair
print(f"Selected interface surfaces: bottom {s_bot}, top {s_top}")


# -------------------------------------------------
# 6. Exterior (non-interface) faces of each body
# -------------------------------------------------
interface_set = {s_bot, s_top}

def exterior_surfaces(vol_id):
    surfs = cubit.parse_cubit_list("surface", f"in volume {vol_id}")
    return [s for s in surfs if cubit.parse_cubit_list("volume", f"in surface {s}") == [vol_id]]

ext_surfs_bot = exterior_surfaces(bottom_vol)
ext_surfs_top = exterior_surfaces(top_vol)
print(f"Exterior bottom faces: {ext_surfs_bot}")
print(f"Exterior top faces   : {ext_surfs_top}")

# -------------------------------------------------
# 7. Move top body and create loft volume
# -------------------------------------------------
cubit.cmd(f"move volume {top_vol} x 0 y 0 z {gap} include_merged")
cubit.cmd(f"create volume loft surface {s_bot},{s_top}")
v_cohesive = cubit.get_last_id("volume")
cubit.cmd("imprint all")
cubit.cmd("merge all")

for v in cubit.get_entities("volume"):
    surfs = cubit.parse_cubit_list("surface", f"in volume {v}")
    print(f"Volume {v} has {len(surfs)} surfaces: {surfs}")

# -------------------------------------------------
# 8. Mesh all volumes
# -------------------------------------------------
for v in cubit.get_entities("volume"):
    cubit.cmd(f"volume {v} size {mesh_size}")
    cubit.cmd(f"mesh volume {v}")

# -------------------------------------------------
# 9. Re-compute exterior faces NOW  ← NEW LOCATION
# -------------------------------------------------
def exterior_surfaces(vol_id):
    return cubit.parse_cubit_list("surface", f"in volume {vol_id}")

ext_surfs_bot = exterior_surfaces(bottom_vol)
ext_surfs_top = exterior_surfaces(top_vol)
print("Exterior (final) bottom faces:", ext_surfs_bot)
print("Exterior (final) top faces   :", ext_surfs_top)


# -------------------------------------------------
# 10. Node sets for outer faces (excluding interface)
# -------------------------------------------------
def surface_normal(s): return cubit.get_surface_normal(s)

def orient_tag(s):
    nx, ny, nz = map(abs, surface_normal(s))
    if nx > ny and nx > nz:
        return 'X+' if surface_normal(s)[0] > 0 else 'X-'
    elif ny > nx and ny > nz:
        return 'Y+' if surface_normal(s)[1] > 0 else 'Y-'
    else:
        return 'Z+' if surface_normal(s)[2] > 0 else 'Z-'

surf_map = defaultdict(list)
for vol, label, faces in [(bottom_vol, "bottom", ext_surfs_bot), (top_vol, "top", ext_surfs_top)]:
    for s in faces:
        surf_map[f"{label}-{orient_tag(s)}"].append(s)

ns_id = 1
nodesets = {}  
for name, faces in surf_map.items():
    for s in faces:
        cubit.cmd(f"nodeset {ns_id} add node in surface {s}")  # 🔧 ensure node-based
    cubit.cmd(f'nodeset {ns_id} name "{name}"')
    nodesets[name] = ns_id 
    print(f"Nodeset {ns_id}: {name} -> faces {faces}")
    ns_id += 1

#------------------------------
#11. Save file to Abaqus format
#------------------------------

success = cubit.cmd(f'export abaqus "three_body_mesh_{cut_angle}_{mesh_size}.inp" mesh_only overwrite everything')
if not success:
    raise RuntimeError("Abaqus export failed — check mesh status and surface assignments.")


# -------------------------------------------------
# 12. Extract and write include files
# -------------------------------------------------

# 1. Nodes
all_nodes = cubit.get_entities("node")
node_coords = {nid: cubit.get_nodal_coordinates(nid) for nid in all_nodes}

with open("include_nodes.inp", "w") as f:
    for nid in sorted(node_coords):
        x, y, z = node_coords[nid]
        f.write(f"{nid}, {x}, {y}, {z}\n")

# 2. Element sets (general element type)
vol_region_map = {"bottom": bottom_vol,"interface": v_cohesive,"top": top_vol}
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
    with open(f"include_elset_{name}.inp", "w") as f:
        for eid, conn in sorted(elems.items()):
            if isinstance(conn, int):
                conn = [conn]
            f.write(f"{eid}, {', '.join(map(str, conn))}\n")

# 3. Nodesets
nodeset_data = {}
for name, nsid in nodesets.items():
    node_ids = cubit.parse_cubit_list("node", f"in nodeset {nsid}")
    if isinstance(node_ids, int):
        node_ids = [node_ids]
    nodeset_data[name] = node_ids
    print(f"Nodeset '{name}' has {len(node_ids)} nodes")

for name, node_ids in nodeset_data.items():
    fname = f"include_nset_{name}.inp"
    with open(fname, "w") as f:
        for i, nid in enumerate(sorted(node_ids), 1):
            f.write(f"{nid}, " if i % 8 else f"{nid}\n")
        if i % 8:
            f.write("\n")

print("Mesh include files written:")
print("  - include_nodes.inp")
print("  - include_elset_{bottom, interface, top}.inp")
print("  - include_nset_<name>.inp")
