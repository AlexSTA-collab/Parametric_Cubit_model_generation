# Mesh Generation for Parametric Study

This directory contains scripts to generate **TWO TYPES** of meshes for the parametric study.

## ⚠️ Important: Two Types of Models

### 1. **Full Cauchy Models** (Full Layer Models)
- The thin interface layer is modeled with **solid elements** (C3D8)
- Requires **very fine mesh** in the interface region
- **No interface elements** - everything is continuum
- Used as **reference solution**

### 2. **Interface Models** (Cohesive Zone Models)
- The thin interface layer is modeled with **interface elements** (IQuad4)
- Top and bottom bodies use solid elements
- **Interface elements** connect the two bodies
- Used as **approximate solution** to be validated

**Key Difference:** The Cubit model layer definition differs between these two approaches!

---

## Contents

### Python Scripts (from Case_a)
- `function_three_body_cubit_model.py` - Cubit mesh generation **with cohesive layer**
- `function_three_body_cubit_model_Full_Cauchy.py` - Cubit mesh generation **without cohesive layer** (solid elements only)
- `function_generate_template_file.py` - Generate .inp template files for Interface models
- `function_generate_template_file_Full_Cauchy.py` - Generate .inp template files for Full Cauchy models
- `orientation_fix.py` - Fix interface element orientation
- `create_set_of_parametric_models.py` - Original batch generation script (Interface models)
- `create_set_of_parametric_models_Full_Cauchy.py` - Original batch generation script (Full Cauchy models)

### New Scripts
- `generate_interface_meshes.py` - Generate meshes for Interface models (with cohesive layer)
- `generate_full_cauchy_meshes.py` - Generate meshes for Full Cauchy models (solid elements only)
- `generate_interface_meshes.sh` - Bash wrapper for Interface models
- `generate_full_cauchy_meshes.sh` - Bash wrapper for Full Cauchy models
- `generate_all_meshes.sh` - Generate BOTH types of meshes
- `copy_meshes_to_shared.sh` - Copy generated meshes to shared library

---

## Complete Mesh Generation Workflow

### Step 1: Generate ALL Meshes (Both Types)

**Option A: Generate everything at once**

```bash
bash generate_all_meshes.sh
```

This runs both Interface and Full Cauchy mesh generation.

**Option B: Generate separately**

```bash
# Generate Interface models (with cohesive layer)
bash generate_interface_meshes.sh

# Generate Full Cauchy models (without cohesive layer)
bash generate_full_cauchy_meshes.sh
```

**Output Structure:**
```
mesh_generation/
├── Interface_models/
│   └── angle_10/
│       ├── height_0.001/
│       │   ├── include_nodes.inp
│       │   ├── include_elset_bottom.inp
│       │   ├── include_elset_interface.inp  ← Interface elements
│       │   ├── include_elset_top.inp
│       │   └── include_nset_*.inp
│       ├── height_0.002/
│       └── ...
│
└── Full_layer_models/
    └── angle_10/
        ├── height_0.001/
        │   ├── include_nodes.inp
        │   ├── include_elset_bottom.inp
        │   ├── include_elset_middle.inp     ← Solid elements (refined)
        │   ├── include_elset_top.inp
        │   └── include_nset_*.inp
        ├── height_0.002/
        └── ...
```

Also generates template files:
- `LinearElastic_Interface_Template_three_body_model_angle_10_h_*.inp`
- `LinearElastic_Full_Cauchy_Template_three_body_model_angle_10_h_*.inp`

**Requirements:**
- Cubit/Coreform installed and in PATH
- Python with access to Cubit Python API

### Step 2: Copy Meshes to Shared Library

```bash
bash copy_meshes_to_shared.sh
```

This creates a centralized mesh library that all material families will reference:

**Output:**
```
../mesh_library/
├── Full_layer_models/
│   └── angle_10/
│       ├── height_0.001/ (mesh includes)
│       ├── height_0.002/
│       └── ...
│
├── Interface_models/
│   └── angle_10/
│       ├── height_0.001/ (mesh includes)
│       ├── height_0.002/
│       └── ...
│
└── templates/
    ├── Full_layer_models/
    │   └── *.inp (template files)
    └── Interface_models/
        └── *.inp (template files)
```

**Key Benefit:** All material families (initial, stiff, soft) use the **same meshes**. No duplication!

## Configuration

### Height Values

Edit `generate_interface_meshes.py` to change mesh resolutions:

```python
height_values = [0.001, 0.002, 0.004, 0.006, 0.008, 0.01]
```

### Angles

Edit `generate_interface_meshes.py` to add more angles:

```python
angles = [0, 10]  # Add more angles
```

## Notes on Full Layer Models

**Full layer models** are **full resolution models** where the thin interface is represented by solid elements instead of interface elements. These require:

1. Very fine meshes in the interface region
2. Different template structure (no interface elements)
3. Typically generated separately with refined meshes

For the parametric study, you can either:

### Option A: Generate separate Full_layer_models
Create a separate script similar to `generate_interface_meshes.py` that:
- Uses the same mesh but removes cohesive layer
- Uses solid elements everywhere
- Refines mesh in interface region

### Option B: Reuse Interface model templates
Modify Interface model templates to:
- Replace interface elements with solid elements
- Adjust material properties

### Option C: Use existing meshes from Case_a
If you already have Full_layer_models from Case_a:
```bash
# Copy from Case_a
cp -r ../Case_a/Full_layer_models/*.inp ../initial/angle_10/Full_layer_models/
cp -r ../Case_a/Full_layer_models/*.inp ../stiff/angle_10/Full_layer_models/
cp -r ../Case_a/Full_layer_models/*.inp ../soft/angle_10/Full_layer_models/
```

## Mesh Parameters

The mesh generation uses these parameters:

- **Horizontal curves**: 10 intervals, equal spacing
- **Vertical curves**: Logarithmic intervals based on gap size
  - `vertical_interval = int(-log10(gap) * 1.0)`
- **Bias factors**: Biased toward interface
  - `bias = (4 + log10(gap) * 0.8) / 5`
- **Interface refinement**: 
  - `numsplit = 1`
  - `bias = 16`
  - `depth = 0.5`

## Troubleshooting

### Problem: Cubit not found
```
❌ ERROR: 'cubit' command not found in PATH
```
**Solution:** Add Cubit to your PATH or use full path to cubit executable

### Problem: Element orientation errors
**Solution:** The `orientation_fix.py` script is automatically applied. Check that `include_elset_interface.inp` was processed.

### Problem: Mesh generation fails for small gaps
**Solution:** The script uses adaptive scaling (`scale_factor = max(1.0, 10.0 * model_size / gap)`) to handle small gaps robustly.

### Problem: Template files have wrong paths
**Solution:** The templates use relative paths. Make sure directory structure matches expected layout.

## File Formats

### Mesh Include Files
- `include_nodes.inp` - Node coordinates
- `include_elset_bottom.inp` - Bottom body hex elements
- `include_elset_interface.inp` - Interface quad elements
- `include_elset_top.inp` - Top body hex elements
- `include_nset_*.inp` - Node sets for boundary conditions

### Template Files
Template .inp files contain placeholders:
- `${E_M}` - Matrix Young's modulus
- `${E_I}` - Interface Young's modulus
- `${E_0}` - Interface stiffness parameter
- `${h}` - Layer height (must match mesh)
- `${angle}` - Angle (informational)

These are substituted by the run scripts during execution.
