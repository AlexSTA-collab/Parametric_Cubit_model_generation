#!/usr/bin/env python3
"""
Compare convergence results across material families (stiff, initial, soft)
"""

import pickle
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# LaTeX rendering
plt.rcParams.update({
    'text.usetex': True,
    'font.family': 'serif',
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'legend.fontsize': 11,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
})

SCRIPT_DIR = Path(__file__).parent
ANGLE = 10
ERROR_METRICS = ['L1', 'L2', 'relL1', 'relL2']
FAMILIES = ['stiff', 'initial', 'soft']

# Get plasma colormap colors
import matplotlib.cm as cm
plasma_cmap = cm.get_cmap('plasma')
plasma_colors = [plasma_cmap(0.15), plasma_cmap(0.5), plasma_cmap(0.85)]

# Family properties for plotting with plasma colors
FAMILY_PROPS = {
    'stiff': {'color': plasma_colors[0], 'marker': 'o', 'label': 'Stiff ($E_0=2\\times10^7$ MPa)'},
    'initial': {'color': plasma_colors[1], 'marker': 's', 'label': 'Initial ($E_0=2\\times10^5$ MPa)'},
    'soft': {'color': plasma_colors[2], 'marker': '^', 'label': 'Soft ($E_0=2\\times10^{-5}$ MPa)'},
}

def load_convergence_data(family, error_type):
    """Load convergence data for a specific family and error type"""
    data = {}
    base_path = SCRIPT_DIR / family / f"angle_{ANGLE}" / "comparison_results" / f"error_{error_type}"
    
    # Load traction jump data
    traction_file = base_path / f"t_i_convergence_{error_type}.pkl"
    if traction_file.exists():
        with open(traction_file, 'rb') as f:
            data['traction'] = pickle.load(f)
    
    # Load displacement jump data
    displacement_file = base_path / f"u_i_convergence_{error_type}.pkl"
    if displacement_file.exists():
        with open(displacement_file, 'rb') as f:
            data['displacement'] = pickle.load(f)
    
    return data

def plot_family_comparison(error_type, quantity, output_dir):
    """Create comparison plot for a specific error metric and quantity across families"""
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    for family in FAMILIES:
        data = load_convergence_data(family, error_type)
        
        if quantity not in data:
            print(f"⚠️  No {quantity} data for {family}/{error_type}")
            continue
        
        conv_data = data[quantity]
        h_values = conv_data['h_values']
        errors = conv_data['mean_errors']
        
        props = FAMILY_PROPS[family]
        ax.loglog(h_values, errors, 
                 marker=props['marker'], 
                 color=props['color'],
                 linewidth=2,
                 markersize=8,
                 label=props['label'])
    
    # Labels and formatting
    quantity_label = "Traction jump $[[\\mathbf{t}]]$" if quantity == 'traction' else "Displacement jump $[[\\mathbf{u}]]$"
    
    error_label_map = {
        'L1': '$L^1$ error',
        'L2': '$L^2$ error', 
        'relL1': 'Relative $L^1$ error',
        'relL2': 'Relative $L^2$ error'
    }
    
    ax.set_xlabel('Interface thickness $h$ [mm]', fontsize=14)
    ax.set_ylabel(f'{error_label_map[error_type]} (MPa)' if quantity == 'traction' else f'{error_label_map[error_type]} (mm)', fontsize=14)
    ax.set_title(f'{error_label_map[error_type]}: {quantity_label}', fontsize=15)
    ax.legend(loc='best', frameon=True, shadow=True)
    
    # Limit number of ticks to 4-6
    from matplotlib.ticker import LogLocator, NullFormatter
    ax.xaxis.set_major_locator(LogLocator(numticks=5))
    ax.yaxis.set_major_locator(LogLocator(numticks=5))
    ax.xaxis.set_minor_locator(LogLocator(subs='auto', numticks=12))
    ax.yaxis.set_minor_locator(LogLocator(subs='auto', numticks=12))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    
    # Tick marks point inward
    ax.tick_params(axis='both', which='both', direction='in', top=True, right=True)
    
    plt.tight_layout()
    
    # Save
    output_file = output_dir / f"family_comparison_{quantity}_{error_type}.pdf"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"💾 Saved: {output_file}")
    plt.close()

def create_summary_table(output_dir):
    """Create a summary table comparing convergence rates across families"""
    
    print("\n" + "="*80)
    print("CONVERGENCE RATE COMPARISON ACROSS FAMILIES")
    print("="*80)
    
    summary_data = {}
    
    for error_type in ERROR_METRICS:
        print(f"\n{error_type} Error:")
        print("-" * 80)
        
        for quantity in ['traction', 'displacement']:
            print(f"\n  {quantity.upper()} JUMP:")
            print(f"  {'Family':<12} {'Rate':<12} {'h=0.01':<15} {'h=0.1':<15}")
            print(f"  {'-'*54}")
            
            for family in FAMILIES:
                data = load_convergence_data(family, error_type)
                
                if quantity in data:
                    conv_data = data[quantity]
                    rate = conv_data.get('convergence_rate', np.nan)
                    errors = conv_data['mean_errors']
                    
                    print(f"  {family:<12} {rate:>8.4f}    {errors[0]:>12.4e}  {errors[-1]:>12.4e}")
                    
                    # Store for summary
                    key = f"{error_type}_{quantity}"
                    if key not in summary_data:
                        summary_data[key] = {}
                    summary_data[key][family] = {
                        'rate': rate,
                        'error_min': errors[0],
                        'error_max': errors[-1]
                    }
    
    # Save summary to file
    summary_file = output_dir / "family_comparison_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("CONVERGENCE RATE COMPARISON ACROSS FAMILIES\n")
        f.write("="*80 + "\n\n")
        
        for error_type in ERROR_METRICS:
            f.write(f"\n{error_type} Error:\n")
            f.write("-" * 80 + "\n")
            
            for quantity in ['traction', 'displacement']:
                f.write(f"\n  {quantity.upper()} JUMP:\n")
                f.write(f"  {'Family':<12} {'Rate':<12} {'h=0.01':<15} {'h=0.1':<15}\n")
                f.write(f"  {'-'*54}\n")
                
                key = f"{error_type}_{quantity}"
                if key in summary_data:
                    for family in FAMILIES:
                        if family in summary_data[key]:
                            data = summary_data[key][family]
                            f.write(f"  {family:<12} {data['rate']:>8.4f}    {data['error_min']:>12.4e}  {data['error_max']:>12.4e}\n")
    
    print(f"\n💾 Summary saved: {summary_file}")
    
    return summary_data

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        FAMILY COMPARISON: CONVERGENCE ANALYSIS               ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    # Create output directory
    output_dir = SCRIPT_DIR / "family_comparison"
    output_dir.mkdir(exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    print()
    
    # Generate comparison plots for each error metric and quantity
    print("🎨 Generating comparison plots...")
    for error_type in ERROR_METRICS:
        for quantity in ['traction', 'displacement']:
            print(f"  - {error_type} / {quantity}")
            plot_family_comparison(error_type, quantity, output_dir)
    
    print()
    
    # Create summary table
    summary_data = create_summary_table(output_dir)
    
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              FAMILY COMPARISON COMPLETED                     ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"Results location: {output_dir}")
    print(f"  - Comparison plots: family_comparison_*.pdf")
    print(f"  - Summary table: family_comparison_summary.txt")
    print()

if __name__ == "__main__":
    main()
