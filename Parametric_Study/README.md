# Parametric Convergence Study Workflow

This directory contains a clean, production-ready parametric study framework for cohesive zone model convergence analysis.

## Directory Structure

```
Parametric_Study/
├── mesh_generation/          # ⭐ CENTRALIZED MESH DATA (Single Source of Truth)
│   ├── config_parametric_study.py              # Configuration: angles, heights, parameters
│   ├── generate_interface_meshes.py            # Generate interface model meshes
│   ├── generate_full_cauchy_meshes.py          # Generate full layer reference meshes
│   ├── function_three_body_cubit_model.py      # Interface mesh generation functions
│   ├── function_three_body_cubit_model_Full_Cauchy.py  # Full model generation functions
│   ├── function_generate_template_file.py      # Interface template generator
│   ├── function_generate_template_file_Full_Cauchy.py  # Full template generator
│   ├── orientation_fix.py                      # Mesh orientation correction
│   ├── run_mesh_generation.sh                  # Orchestrator for mesh generation
│   ├── Interface_models/                       # Interface templates + mesh data
│   │   ├── LinearElastic_Interface_Template_*.inp   # Templates (material params as $E_M, $E_I, $E_0)
│   │   └── angle_{X}/height_{h}/               # Include files (nodes, elements, nsets)
│   └── Full_layer_models/                      # Full model templates + mesh data
│       ├── LinearElastic_Full_Cauchy_Template_*.inp
│       └── angle_{X}/height_{h}/
├── evaluation_scripts/       # Centralized evaluation scripts (used by all families)
│   ├── Interface_Model_Evaluate_traction_jump.py
│   ├── Interface_Model_Evaluate_displacement_jump.py
│   ├── Full_Model_Evaluate_traction_jump.py
│   └── Full_Model_Evaluate_displacement_jump.py
├── scripts/                  # Organized workflow and analysis scripts
│   ├── workflow/
│   │   └── run_master_workflow.sh              # Main workflow orchestrator
│   └── postprocessing/
│       ├── convergence_analysis.py             # Parametrized convergence analysis
│       └── master_parametric_script.py         # Generate cross-family comparison plots
├── stiff/                    # Stiff material family (E_M=2e5, E_I=4e3, E_0=4e5)
│   └── angle_{X}/
│       ├── Interface_models/                   # Job files + analysis results
│       │   ├── *_job.inp                       # Generated with family-specific materials
│       │   ├── *.case                          # Solver output
│       │   └── cases/*.pkl                     # Postprocessing results
│       ├── Full_layer_models/                  # Job files + analysis results
│       └── comparison_results/                 # Convergence analysis outputs
├── initial/                  # Initial material family (E_M=2e5, E_I=4e3, E_0=4e3)
│   └── angle_{X}/
├── soft/                     # Soft material family (E_M=2e5, E_I=4e3, E_0=4e-5)
│   └── angle_{X}/
├── comparison_plots/         # Cross-family comparative plots
│   └── angle_{X}/
│       ├── L1/
│       ├── L2/
│       ├── relL1/
│       └── relL2/
├── run_workflow.sh           # Convenience wrapper for main workflow
└── generate_plots.sh         # Convenience wrapper for plot generation
```

## Architecture Philosophy

**Key Design Principle: Separation of Mesh Data and Material Parameters**

The architecture follows a clean separation:

1. **`mesh_generation/`** (READ-ONLY after generation):
   - Contains ALL mesh geometry data (nodes, elements, node sets)
   - Contains template files with material parameters as variables (`$E_M`, `$E_I`, `$E_0`)
   - **Single source of truth** for mesh data
   - Shared by all material families

2. **`{family}/angle_{X}/`** (WORKING DIRECTORIES):
   - Contains ONLY job files (templates + material-specific values)
   - Contains analysis results (.case files, .pkl files)
   - References centralized mesh data via absolute paths
   - Each family has its own results, but shares mesh geometry

**Benefit**: No data duplication. Templates and mesh data stored once, used by all families.

## Configuration

All parametric study settings are centralized in:
```
mesh_generation/config_parametric_study.py
```

Key settings:
- `ANGLES`: List of angles to study (e.g., [0, 10])
- `HEIGHT_VALUES_INTERFACE`: Interface layer thicknesses
- `HEIGHT_VALUES_FULL`: Reference full layer thickness (typically [0.01])
- `MATERIAL_FAMILIES`: Dictionary defining stiff/initial/soft parameters

## Workflow

### 1. Generate Meshes (One-Time Setup)
```bash
cd mesh_generation
./run_mesh_generation.sh
```
This generates:
- Templates with parametrized materials (`.inp` files with `$E_M`, `$E_I`, `$E_0` placeholders)
- Mesh geometry data (nodes, elements, node sets)
- All stored in centralized `mesh_generation/` directory

**Note**: After mesh generation, `mesh_generation/` becomes READ-ONLY and is shared by all analyses.

### 2. Run Complete Study
```bash
# Run specific family and angle
./scripts/workflow/run_master_workflow.sh <family> <angle>

# Run all families for specific angle
./scripts/workflow/run_master_workflow.sh all 0

# Run all families and all angles
./scripts/workflow/run_master_workflow.sh all all
```

**What happens internally**:
1. **Job File Generation**: Creates `*_job.inp` files in family directories by:
   - Reading templates from centralized `mesh_generation/`
   - Substituting material parameters (E_M, E_I, E_0) for specific family
   - Updating include paths to point to centralized mesh data
   
2. **FE Analysis**: Runs solver in family directories
   - Reads job file from family directory
   - Reads mesh data from centralized `mesh_generation/`
   - Writes results (.case files) to family directory

3. **Postprocessing**: Extracts traction/displacement jumps

4. **Convergence Analysis**: Generates error metrics (L1, L2, relL1, relL2)

### 3. Generate Cross-Family Comparative Plots
```bash
./generate_plots.sh
```
Generates 16 plots comparing all families across:
- 2 angles
- 2 quantities (traction_jump, displacement_jump)
- 4 error types (L1, L2, relL1, relL2)

Plots saved to: `comparison_plots/angle_{X}/{error_type}/comparison_{quantity}.pdf`

## Key Scripts

### Workflow Scripts (`scripts/workflow/`)

**run_master_workflow.sh**
- Main workflow orchestrator
- Runs simulations and convergence analysis
- Usage: `./run_workflow.sh <family> <angle>` or `./run_workflow.sh all <angle>`

**deploy_meshes.sh**
- Deploys generated meshes to all material families
- Copies from mesh_library to family directories

### Postprocessing Scripts (`scripts/postprocessing/`)

**convergence_analysis.py**
- Parametrized script for convergence analysis
- Automatically processes ALL error types (L1, L2, relL1, relL2)
- Usage: `python3 scripts/postprocessing/convergence_analysis.py <family> <angle>`
- Output: 8 files per run (2 quantities × 4 error types)
  - Location: `{family}/angle_{X}/comparison_results/`
  - Format: `convergence_{Quantity}_{error_type}.pkl` and `.pdf`

**master_parametric_script.py**
- Generates cross-family comparative plots with plasma colormap
- Automatic processing of all error types
- Organized output directory structure (angle → error type → plots)
- Usage: `./generate_plots.sh`
- Output: Publication-ready PDF plots in `comparison_plots/`

## Material Families

| Family  | E_M    | E_I  | E_0    |
|---------|--------|------|--------|
| stiff   | 2×10⁵  | 4×10³| 4×10⁵  |
| initial | 2×10⁴  | 4×10³| 4×10⁴  |
| soft    | 2×10³  | 4×10³| 4×10⁻⁵ |

## Output Files

### Per-Family Results
- `{family}/angle_{X}/comparison_results/convergence_{Quantity}_{error_type}.pkl`
- `{family}/angle_{X}/comparison_results/convergence_{Quantity}_{error_type}.pdf`

### Comparative Plots
- `comparison_plots/angle_{X}/{error_type}/comparison_{quantity}.pdf`

## Requirements

- Coreform Cubit 2025.8+
- Python 3.x with matplotlib, numpy, pickle
- Edelweiss FEM solver
- ParaView (for post-processing)

## Notes

- All error types (L1, L2, relL1, relL2) are computed automatically
- Plasma colormap used for family differentiation in plots
- Configuration changes require re-running mesh generation
- Scripts follow DRY principle - no duplication
