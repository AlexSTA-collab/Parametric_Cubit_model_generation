#!/usr/bin/env python3
"""
Central configuration file for parametric study.
All mesh generation scripts should import parameters from here.
"""

# ===========================================================================
# GEOMETRIC PARAMETERS
# ===========================================================================

# Angles to study (degrees)
ANGLES = [0, 10]

# Layer heights for convergence study (meters)
# Interface models: multiple heights for convergence analysis
HEIGHT_VALUES_INTERFACE = [0.1, 0.08, 0.06, 0.04, 0.02, 0.01]

# Full Cauchy models: only reference height
HEIGHT_VALUES_FULL = [0.01]

# ===========================================================================
# MATERIAL FAMILIES
# ===========================================================================

MATERIAL_FAMILIES = {
    "stiff": {
        "E_M": 2e5,   # Matrix Young's modulus [MPa]
        "E_I": 4e3,   # Interface stiffness [MPa/mm]
        "E_0": 4e7,   # Interface penalty stiffness [MPa/mm]
    },
    "initial": {
        "E_M": 2e4,   # Matrix Young's modulus [MPa]
        "E_I": 4e2,   # Interface stiffness [MPa/mm]
        "E_0": 4e6,   # Interface penalty stiffness [MPa/mm]
    },
    "soft": {
        "E_M": 2e3,   # Matrix Young's modulus [MPa]
        "E_I": 4e1,   # Interface stiffness [MPa/mm]
        "E_0": 4e5,   # Interface penalty stiffness [MPa/mm]
    },
}

# ===========================================================================
# DIRECTORIES
# ===========================================================================

OUTPUT_DIR_INTERFACE = "Interface_models"
OUTPUT_DIR_FULL = "Full_layer_models"

# ===========================================================================
# PRINTING
# ===========================================================================

def print_config():
    """Print current configuration"""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           PARAMETRIC STUDY CONFIGURATION                  ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print(f"Angles: {ANGLES}°")
    print(f"Interface heights: {HEIGHT_VALUES_INTERFACE} m")
    print(f"Full Cauchy heights: {HEIGHT_VALUES_FULL} m")
    print()
    print("Material families:")
    for name, params in MATERIAL_FAMILIES.items():
        print(f"  {name}:")
        print(f"    E_M = {params['E_M']:.1e} MPa")
        print(f"    E_I = {params['E_I']:.1e} MPa/mm")
        print(f"    E_0 = {params['E_0']:.1e} MPa/mm")
    print()


if __name__ == "__main__":
    print_config()
