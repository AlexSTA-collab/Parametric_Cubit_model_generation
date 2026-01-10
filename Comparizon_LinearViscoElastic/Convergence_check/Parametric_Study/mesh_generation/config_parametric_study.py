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

# Viscoelastic parameters that remain constant across all families
VISCOELASTIC_CONSTANTS = {
    "nKelvin": 1,          # Number of Kelvin units
    "minTau": 1e-2,        # Minimum relaxation time
    "timeToDays": 1e0,     # Time conversion factor
    "MaterialID": 0,       # Material identifier
}

# m parameter values (elastic stiffness parameter)
M_VALUES = {
    "elastic_limit": 1e3,      # Nearly elastic behavior
    "viscoelastic": 1e-1,       # Intermediate viscoelastic behavior
    "viscous_limit": 1e-3,     # Nearly viscous behavior
}

# n parameter values (viscous stiffness parameter)
N_VALUES = [4e-5, 4e5]

MATERIAL_FAMILIES = {
    "stiff": {
        "E_M": 2e5,   # Matrix Young's modulus [MPa]
        "E_I": 4e3,   # Inclusion stiffness [MPa/mm]
        "E_0": 4e5,   # Interface stiffness [MPa/mm]
        # Viscoelastic parameter combinations (m, n)
        "viscoelastic_params": 
            [
            {"m": M_VALUES["elastic_limit"], "n": n, **VISCOELASTIC_CONSTANTS}
            for n in N_VALUES] + 
            [
            {"m": M_VALUES["viscoelastic"], "n": n, **VISCOELASTIC_CONSTANTS}
            for n in N_VALUES] + 
            [
            {"m": M_VALUES["viscous_limit"], "n": n, **VISCOELASTIC_CONSTANTS}
            for n in N_VALUES
        ],
    },
    "initial": {
        "E_M": 2e5,   # Matrix Young's modulus [MPa]
        "E_I": 4e3,   # Inclusion stiffness [MPa/mm]
        "E_0": 4e3,   # Interface stiffness [MPa/mm]
        # Viscoelastic parameter combinations (m, n)
        "viscoelastic_params": 
            [
            {"m": M_VALUES["elastic_limit"], "n": n, **VISCOELASTIC_CONSTANTS}
            for n in N_VALUES] + 
            [
            {"m": M_VALUES["viscoelastic"], "n": n, **VISCOELASTIC_CONSTANTS}
            for n in N_VALUES] + 
            [
            {"m": M_VALUES["viscous_limit"], "n": n, **VISCOELASTIC_CONSTANTS}
            for n in N_VALUES
            ],
    },
    "soft": {
        "E_M": 2e5,   # Matrix Young's modulus [MPa]
        "E_I": 4e3,   # Inclusion stiffness [MPa/mm]
        "E_0": 4e-5,   # Interface stiffness [MPa/mm]
        # Viscoelastic parameter combinations (m, n)
        "viscoelastic_params": 
           [
           {"m": M_VALUES["elastic_limit"], "n": n, **VISCOELASTIC_CONSTANTS}
           for n in N_VALUES] + 
            [
            {"m": M_VALUES["viscoelastic"], "n": n, **VISCOELASTIC_CONSTANTS}
            for n in N_VALUES] + 
            [
            {"m": M_VALUES["viscous_limit"], "n": n, **VISCOELASTIC_CONSTANTS}
            for n in N_VALUES
            ],
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

def get_viscoelastic_params(family_name):
    """
    Get all viscoelastic parameter combinations for a given family.
    
    Args:
        family_name: str, one of 'stiff', 'initial', 'soft'
    
    Returns:
        list of dicts, each containing: m, n, nKelvin, minTau, timeToDays, MaterialID
    """
    if family_name not in MATERIAL_FAMILIES:
        raise ValueError(f"Unknown family: {family_name}. Available: {list(MATERIAL_FAMILIES.keys())}")
    return MATERIAL_FAMILIES[family_name]["viscoelastic_params"]


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
    print("Viscoelastic constants (fixed across all families):")
    for key, value in VISCOELASTIC_CONSTANTS.items():
        print(f"  {key} = {value}")
    print()
    print("Material families:")
    for name, params in MATERIAL_FAMILIES.items():
        print(f"  {name}:")
        print(f"    E_M = {params['E_M']:.1e} MPa")
        print(f"    E_I = {params['E_I']:.1e} MPa/mm")
        print(f"    E_0 = {params['E_0']:.1e} MPa/mm")
        print(f"    Viscoelastic parameter sets: {len(params['viscoelastic_params'])} combinations")
        print(f"      m values: {list(M_VALUES.values())}")
        print(f"      n values: {N_VALUES}")
        print(f"      → Total: {len(params['viscoelastic_params'])} (m,n) pairs")
    print()
    print(f"Total study size:")
    print(f"  Families: {len(MATERIAL_FAMILIES)}")
    print(f"  Angles: {len(ANGLES)}")
    print(f"  Heights: {len(HEIGHT_VALUES_INTERFACE)}")
    print(f"  Viscoelastic combos per family: {len(MATERIAL_FAMILIES['stiff']['viscoelastic_params'])}")
    total_runs = len(MATERIAL_FAMILIES) * len(ANGLES) * len(HEIGHT_VALUES_INTERFACE) * len(MATERIAL_FAMILIES['stiff']['viscoelastic_params'])
    print(f"  → Total Interface model runs: {total_runs}")
    print()


if __name__ == "__main__":
    print_config()
