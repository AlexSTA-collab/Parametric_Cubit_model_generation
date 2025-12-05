# Parametric Study - Directory Organization

## Structure Overview

The Parametric Study directory is organized into logical groups for maintainability and clarity.

```
Parametric_Study/
├── 📂 mesh_generation/        ← All mesh-related scripts
├── 📂 scripts/
│   ├── workflow/              ← Workflow orchestration
│   └── postprocessing/        ← Analysis & visualization
├── 📂 mesh_library/           ← Template storage
├── 📂 stiff/                  ← Material family results
├── 📂 initial/                ← Material family results
├── 📂 soft/                   ← Material family results
├── 📂 comparison_plots/       ← Cross-family plots
├── 🔧 run_workflow.sh         ← Quick access wrapper
├── 🔧 generate_plots.sh       ← Quick access wrapper
└── 📄 README.md               ← Complete documentation
```

## Script Categories

### 1. Mesh Generation (`mesh_generation/`)
**Purpose:** Generate all required meshes for parametric study

**Scripts:**
- `config_parametric_study.py` - **SINGLE SOURCE OF TRUTH** for all parameters
- `generate_interface_meshes.py` - Generate interface models
- `generate_full_cauchy_meshes.py` - Generate full reference models
- `function_three_body_cubit_model.py` - Interface mesh functions
- `function_three_body_cubit_model_Full_Cauchy.py` - Full model functions
- `function_generate_template_file.py` - Interface template generator
- `function_generate_template_file_Full_Cauchy.py` - Full template generator
- `orientation_fix.py` - Mesh orientation correction
- `run_mesh_generation.sh` - Orchestrator script

**Usage:**
```bash
cd mesh_generation
./run_mesh_generation.sh
```

### 2. Workflow Scripts (`scripts/workflow/`)
**Purpose:** Orchestrate complete study workflows

**Scripts:**
- `run_master_workflow.sh` - Main workflow orchestrator
  - Runs interface models
  - Runs full reference model
  - Performs convergence analysis
  - Generates individual family plots
  
- `deploy_meshes.sh` - Deploy meshes to families
  - Copies from mesh_library to family directories
  - Updates all three material families

**Usage:**
```bash
# Via wrapper (recommended)
./run_workflow.sh stiff 0

# Direct access
./scripts/workflow/run_master_workflow.sh all 10
```

### 3. Postprocessing Scripts (`scripts/postprocessing/`)
**Purpose:** Analyze results and generate visualizations

**Scripts:**
- `convergence_analysis.py` - Convergence analysis
  - Automatically processes ALL error types (L1, L2, relL1, relL2)
  - Computes convergence rates
  - Generates pickled results and plots
  - Called automatically by run_master_workflow.sh
  
- `master_parametric_script.py` - Cross-family comparison plots
  - Compares all three families (stiff, initial, soft)
  - Processes all error types automatically
  - Uses plasma colormap
  - Organized output structure: `angle_{X}/{error_type}/`

**Usage:**
```bash
# Individual family analysis (usually called by workflow)
python3 scripts/postprocessing/convergence_analysis.py stiff 0

# Generate all comparative plots
./generate_plots.sh
```

## Convenience Wrappers

Two wrapper scripts in the main directory provide quick access:

### `run_workflow.sh`
Wrapper for `scripts/workflow/run_master_workflow.sh`

```bash
./run_workflow.sh <family> <angle>
./run_workflow.sh all <angle>
```

### `generate_plots.sh`
Wrapper for `scripts/postprocessing/master_parametric_script.py`

```bash
./generate_plots.sh
```

## Design Principles

### Separation of Concerns
1. **Mesh scripts** in `mesh_generation/` - isolated from execution
2. **Workflow scripts** in `scripts/workflow/` - orchestration only
3. **Postprocessing** in `scripts/postprocessing/` - analysis and visualization

### Single Source of Truth
All parameters centralized in `mesh_generation/config_parametric_study.py`:
- Angles to study
- Height values
- Material properties
- Family definitions

### DRY Principle
- No duplicate scripts
- Parametrized implementations
- Reusable components

### Discoverability
- Clear directory names
- Logical grouping
- Convenience wrappers at top level
- Comprehensive README

## Common Workflows

### Complete Study from Scratch
```bash
# 1. Generate meshes
cd mesh_generation
./run_mesh_generation.sh
cd ..

# 2. Deploy to families
./scripts/workflow/deploy_meshes.sh

# 3. Run simulations and analysis
./run_workflow.sh all 0    # Angle 0
./run_workflow.sh all 10   # Angle 10

# 4. Generate comparative plots
./generate_plots.sh
```

### Re-run Analysis Only
```bash
# Re-analyze specific family
python3 scripts/postprocessing/convergence_analysis.py stiff 0

# Regenerate all comparative plots
./generate_plots.sh
```

### Add New Angle
```bash
# 1. Update config
nano mesh_generation/config_parametric_study.py
# Add angle to ANGLES list

# 2. Generate meshes for new angle
cd mesh_generation
./run_mesh_generation.sh
cd ..

# 3. Deploy and run
./scripts/workflow/deploy_meshes.sh
./run_workflow.sh all <new_angle>

# 4. Update plots
./generate_plots.sh
```

## File Locations

### Input Files
- Meshes: `mesh_library/Interface_models/`, `mesh_library/Full_layer_models/`
- Templates: `{family}/angle_{X}/*_templates/`

### Output Files
- Simulation results: `{family}/angle_{X}/Interface_models/`, `Full_layer_models/`
- Convergence data: `{family}/angle_{X}/comparison_results/*.pkl`
- Individual plots: `{family}/angle_{X}/comparison_results/*.pdf`
- Comparative plots: `comparison_plots/angle_{X}/{error_type}/*.pdf`

## Maintenance

### Adding a Script
1. Determine category (mesh, workflow, postprocessing)
2. Place in appropriate directory
3. Update this documentation
4. Consider adding wrapper if frequently used

### Modifying Parameters
- **Always** edit `mesh_generation/config_parametric_study.py`
- Never hardcode values in individual scripts
- Regenerate meshes after parameter changes

### Cleaning Up
- Results cleaned per-run (automatic)
- Logs not generated (clean workflow)
- To reset: remove family angle directories and regenerate

## Migration Notes

**Previous Structure (Pre-December 5, 2025):**
- Scripts scattered in main directory
- No logical grouping
- Difficult to navigate

**Current Structure:**
- Organized into `scripts/workflow/` and `scripts/postprocessing/`
- Mesh scripts remain in `mesh_generation/` (already well-organized)
- Convenience wrappers maintain backward compatibility
- Clear separation of concerns

All existing workflows continue to function with new wrapper scripts.
