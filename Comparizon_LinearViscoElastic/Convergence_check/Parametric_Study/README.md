# Parametric Convergence Study Workflow

This directory contains a clean, production-ready parametric study framework for cohesive zone model convergence analysis.

## Recent Updates (December 2025)

✨ **New Features:**
- **`run_complete_study.sh`**: Single-command complete workflow (mesh check + all analyses + plots)
- **Auto-Directory Creation**: Family directories created automatically - no manual setup needed
- **Fresh Start Scripts**: `cleanup_families.sh` and `setup_and_run.sh` for easy resets
- **Enhanced Documentation**: QUICK_START.txt, SETUP_SUMMARY.txt, WORKFLOW_DIAGRAM.txt

🎯 **Quick Start:**
```bash
./run_complete_study.sh  # Run everything - that's it!
```

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
│   └── angle_{X}/            # Auto-created by workflow
│       ├── Interface_models/                   # Job files + analysis results
│       │   ├── *_job.inp                       # Generated with family-specific materials
│       │   ├── *.case                          # Solver output
│       │   └── cases/*.pkl                     # Postprocessing results
│       ├── Full_layer_models/                  # Job files + analysis results
│       └── comparison_results/                 # Convergence analysis outputs
├── initial/                  # Initial material family (E_M=2e5, E_I=4e3, E_0=4e3)
│   └── angle_{X}/            # Auto-created by workflow
├── soft/                     # Soft material family (E_M=2e5, E_I=4e3, E_0=4e-5)
│   └── angle_{X}/            # Auto-created by workflow
├── comparison_plots/         # Cross-family comparative plots (auto-created)
│   └── angle_{X}/
│       ├── L1/
│       ├── L2/
│       ├── relL1/
│       └── relL2/
├── run_complete_study.sh     # ⭐ Complete study: mesh check + all analyses + plots
├── run_workflow.sh           # Convenience wrapper for main workflow
├── cleanup_families.sh       # Clean all family directories (interactive)
├── setup_and_run.sh          # Fresh start: cleanup + run workflow
├── generate_plots.sh         # Convenience wrapper for plot generation
├── QUICK_START.txt           # Quick start guide
├── SETUP_SUMMARY.txt         # Complete reference documentation
└── WORKFLOW_DIAGRAM.txt      # Visual workflow diagram
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

### Quick Start (Complete Study)

**Option 1: Run Everything (Recommended)**
```bash
./run_complete_study.sh
```
This single command:
1. Checks mesh generation (verifies templates and mesh data exist)
2. Runs FE analyses for all families (stiff, initial, soft) and all angles (0, 10)
3. Generates cross-family comparative plots
4. Automatically creates family directories as needed

**Option 2: Fresh Start (Clean Slate)**
```bash
./setup_and_run.sh [family] [angle]
```
Removes all existing family directories, recreates structure, and runs workflow.

**Option 3: Clean Only**
```bash
./cleanup_families.sh
```
Interactive cleanup - removes all family directories (requires confirmation).

### Manual Workflow Steps

#### 1. Generate Meshes (One-Time Setup)
```bash
cd mesh_generation
./run_mesh_generation.sh
```
This generates:
- Templates with parametrized materials (`.inp` files with `$E_M`, `$E_I`, `$E_0` placeholders)
- Mesh geometry data (nodes, elements, node sets)
- All stored in centralized `mesh_generation/` directory

**Note**: After mesh generation, `mesh_generation/` becomes READ-ONLY and is shared by all analyses.

#### 2. Run Specific Analyses
```bash
# Run specific family and angle
./scripts/workflow/run_master_workflow.sh <family> <angle>

# Run all families for specific angle
./scripts/workflow/run_master_workflow.sh all 0

# Run all families and all angles
./scripts/workflow/run_master_workflow.sh all all
```

**What happens internally**:
1. **Directory Creation**: Automatically creates family/angle directory structure if missing
2. **Job File Generation**: Creates `*_job.inp` files in family directories by:
   - Reading templates from centralized `mesh_generation/`
   - Substituting material parameters (E_M, E_I, E_0) for specific family
   - Updating include paths to point to centralized mesh data
3. **FE Analysis**: Runs solver in family directories
   - Reads job file from family directory
   - Reads mesh data from centralized `mesh_generation/`
   - Writes results (.case files) to family directory
4. **Postprocessing**: Extracts traction/displacement jumps
5. **Convergence Analysis**: Generates error metrics (L1, L2, relL1, relL2)

#### 3. Generate Cross-Family Comparative Plots
```bash
./generate_plots.sh
```
Generates 16 plots comparing all families across:
- 2 angles
- 2 quantities (traction_jump, displacement_jump)
- 4 error types (L1, L2, relL1, relL2)

Plots saved to: `comparison_plots/angle_{X}/{error_type}/comparison_{quantity}.pdf`

## Key Scripts

### Top-Level Scripts

**run_complete_study.sh** ⭐
- Complete parametric study workflow (mesh check + analyses + plots)
- Auto-creates family directories as needed
- Usage: `./run_complete_study.sh`

**setup_and_run.sh**
- Fresh start workflow (cleanup + recreate + run)
- Usage: `./setup_and_run.sh [family] [angle]`

**cleanup_families.sh**
- Interactive cleanup of all family directories
- Requires "yes" confirmation
- Usage: `./cleanup_families.sh`

**run_workflow.sh**
- Wrapper for `scripts/workflow/run_master_workflow.sh`
- Usage: `./run_workflow.sh <family> <angle>`

**generate_plots.sh**
- Wrapper for cross-family comparative plots
- Usage: `./generate_plots.sh`

### Workflow Scripts (`scripts/workflow/`)

**run_master_workflow.sh**
- Main workflow orchestrator
- Auto-creates missing family/angle directories
- Runs simulations and convergence analysis
- Usage: `./scripts/workflow/run_master_workflow.sh <family> <angle>`
  - `<family>`: stiff, initial, soft, or "all"
  - `<angle>`: 0, 10, or "all"

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

| Family  | E_M    | E_I  | E_0    | Description |
|---------|--------|------|--------|-------------|
| stiff   | 2×10⁵  | 4×10³| 4×10⁵  | Stiff interface |
| initial | 2×10⁵  | 4×10³| 4×10³  | Initial/reference case |
| soft    | 2×10⁵  | 4×10³| 4×10⁻⁵ | Soft interface |

## Output Files

### Per-Family Results
- `{family}/angle_{X}/comparison_results/convergence_{Quantity}_{error_type}.pkl`
- `{family}/angle_{X}/comparison_results/convergence_{Quantity}_{error_type}.pdf`

### Comparative Plots
- `comparison_plots/angle_{X}/{error_type}/comparison_{quantity}.pdf`

## Documentation Files

- **QUICK_START.txt**: Quick start guide for running studies
- **SETUP_SUMMARY.txt**: Complete reference documentation
- **WORKFLOW_DIAGRAM.txt**: Visual workflow diagram

## Requirements

- Coreform Cubit 2025.8+
- Python 3.x with matplotlib, numpy, pickle
- Edelweiss FEM solver
- ParaView (for post-processing)
- Mamba/Conda environments:
  - `alexandros`: Solver environment
  - `alexandros_Plot`: Visualization environment

## Notes

- **Auto-Creation**: Family directories are automatically created by workflow scripts
- **Fresh Start**: Use `./cleanup_families.sh` to remove all results and start fresh
- **Single Command**: Use `./run_complete_study.sh` to run everything
- **Error Types**: All error types (L1, L2, relL1, relL2) computed automatically
- **Plasma Colormap**: Used for family differentiation in comparative plots
- **Configuration**: Changes require re-running mesh generation
- **DRY Principle**: No code or data duplication
