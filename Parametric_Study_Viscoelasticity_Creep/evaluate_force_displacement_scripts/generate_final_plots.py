#!/usr/bin/env python3

import argparse
import os
import pickle
import numpy as np
from itertools import cycle
from collections import defaultdict

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.ticker import LogLocator, FuncFormatter
from matplotlib.lines import Line2D


# ---------------------------------------------------------------------
# Matplotlib settings
# ---------------------------------------------------------------------
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "font.size": 11,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "savefig.format": "pdf",
    "savefig.bbox": "tight",
    "figure.dpi": 100,
})


# ---------------------------------------------------------------------
# Tick formatters
# ---------------------------------------------------------------------
def y_mantissa_formatter_factory(exponent):
    def formatter(y, pos):
        if y <= 0:
            return ""
        return f"{y / 10**exponent:g}"
    return formatter


def y_mantissa_every_second_formatter_factory(exponent):
    def formatter(y, pos):
        if y <= 0:
            return ""
        return f"{y / 10**exponent:g}" if pos % 2 == 0 else ""
    return formatter


def log10_exponent_formatter(x, pos):
    if x <= 0:
        return ""
    return f"{np.log10(x):.0f}"


# ---------------------------------------------------------------------
def apply_log_axes_with_y_exponent(ax, *, stress=False):
    ax.set_xscale("log")
    ax.set_yscale("log")

    ax.xaxis.set_major_locator(LogLocator(base=10))
    ax.xaxis.set_minor_locator(LogLocator(base=10, subs=(2, 5)))
    ax.xaxis.set_major_formatter(FuncFormatter(log10_exponent_formatter))
    ax.xaxis.offsetText.set_visible(False)

    ymin, ymax = ax.get_ylim()
    y_exp = int(np.floor(np.log10(ymax)))

    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10)))

    ax.yaxis.set_major_formatter(
        FuncFormatter(y_mantissa_formatter_factory(y_exp))
    )

    if stress:
        ax.yaxis.set_minor_formatter(
            FuncFormatter(y_mantissa_every_second_formatter_factory(y_exp))
        )
    else:
        ax.yaxis.set_minor_formatter(
            FuncFormatter(y_mantissa_formatter_factory(y_exp))
        )

    ax.yaxis.offsetText.set_visible(False)

    ax.text(
        0.0, 1.02,
        rf"$\times 10^{{{y_exp}}}$",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
    )

    ax.tick_params(axis="y", which="major", labelsize=12, pad=4)
    ax.tick_params(axis="y", which="minor", labelsize=9, pad=2)


# ---------------------------------------------------------------------
def make_h_legend_and_colorbar(h_vals, h_to_ls, norm, cmap, outdir):
    fig = plt.figure(figsize=(2.8, 3.2))
    gs = fig.add_gridspec(
        2, 1,
        height_ratios=[1.0, 1.35],
        hspace=0.2,
    )

    # ---------------- h legend ----------------
    ax_leg = fig.add_subplot(gs[0, 0])
    ax_leg.axis("off")

    handles = [
        Line2D([0], [0], color="black",
               linestyle=h_to_ls[h], label=rf"${h}$")
        for h in h_vals
    ]

    ax_leg.legend(
        handles=handles,
        title=r"$h$",
        frameon=False,
        loc="lower left",
        handlelength=2.5,
        borderaxespad=0.0,
    )

    # ---------------- colorbar ----------------
    ax_cb = fig.add_subplot(gs[1, 0])
    ax_cb.axis("off")

    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])

    cbar = fig.colorbar(
        sm,
        ax=ax_cb,
        fraction=0.9,
        pad=0.02,
    )

    cbar.ax.yaxis.set_major_locator(LogLocator(base=10))
    cbar.ax.yaxis.set_minor_locator(
        LogLocator(base=10, subs=np.arange(2, 10))
    )
    cbar.ax.yaxis.set_major_formatter(
        FuncFormatter(log10_exponent_formatter)
    )
    cbar.ax.yaxis.offsetText.set_visible(False)

    cbar.set_label(
        r"$\log\!\left(\frac{\overline{E}^0}{E^M + E^I}\right)$",
        rotation=0,
        labelpad=8,
        ha="left",
    )

    fig.savefig(
        os.path.join(outdir, "h_legend_and_colorbar.pdf"),
        bbox_inches="tight",
    )
    plt.close(fig)

# ---------------------------------------------------------------------
def plot_group(select_items, family, angle, b_value, outdir):

    a_vals = np.array([abs(k[0]) for k in select_items])
    norm = LogNorm(vmin=a_vals.min(), vmax=a_vals.max())
    cmap = plt.colormaps["plasma"]

    h_vals = sorted({k[2] for k in select_items})
    linestyle_cycle = cycle(
        ["-", "--", "-.", ":", (0, (5, 1)), (0, (1, 1))]
    )
    h_to_ls = {h: next(linestyle_cycle) for h in h_vals}

    make_h_legend_and_colorbar(h_vals, h_to_ls, norm, cmap, outdir)

    def make_plot(ykey, ylabel, fname):
        epsilon = 1e-8
        fig, ax = plt.subplots(figsize=(5.2, 4.2))
        orig_t_min, orig_t_max = None, None
        orig_y_min, orig_y_max = None, None
        for (a, b, h), entry in select_items.items():
            t = np.array(entry["time"], dtype=float)
            y = np.abs(np.array(entry[ykey], dtype=float))
            # Store original min/max for axis limits
            tmin, tmax = np.min(t[t > 0]), np.max(t)
            ymin, ymax = np.min(y[y > 0]), np.max(y)
            orig_t_min = tmin if orig_t_min is None else min(orig_t_min, tmin)
            orig_t_max = tmax if orig_t_max is None else max(orig_t_max, tmax)
            orig_y_min = ymin if orig_y_min is None else min(orig_y_min, ymin)
            orig_y_max = ymax if orig_y_max is None else max(orig_y_max, ymax)
            # Add epsilon only to first element for plotting
            t_plot = t.copy()
            y_plot = y.copy()
            t_plot[0] += epsilon
            y_plot[0] += epsilon
            ax.plot(
                t_plot,
                y_plot,
                color=cmap(norm(abs(a))),
                linestyle=h_to_ls[h],
            )
        apply_log_axes_with_y_exponent(
            ax, stress=(ykey == "stress")
        )
        # Add padding to axis limits so curves do not fall on the axes
        pad_frac = 0.04
        t_pad = (np.log10(orig_t_max) - np.log10(orig_t_min)) * pad_frac if orig_t_min > 0 and orig_t_max > 0 else 0
        y_pad = (np.log10(orig_y_max) - np.log10(orig_y_min)) * pad_frac if orig_y_min > 0 and orig_y_max > 0 else 0
        tmin_p = 10**(np.log10(orig_t_min) - t_pad) if orig_t_min > 0 else orig_t_min
        tmax_p = 10**(np.log10(orig_t_max) + t_pad) if orig_t_max > 0 else orig_t_max
        ymin_p = 10**(np.log10(orig_y_min) - y_pad) if orig_y_min > 0 else orig_y_min
        ymax_p = 10**(np.log10(orig_y_max) + y_pad) if orig_y_max > 0 else orig_y_max
        ax.set_xlim(tmin_p, tmax_p)
        ax.set_ylim(ymin_p, ymax_p)
        ax.set_xlabel(r"$\log_{10}(t\,[\mathrm{days}])$")
        ax.set_ylabel(ylabel)
        plt.tight_layout()
        fname_full = f"{family}_angle_{angle}_b_{b_value:g}_{fname}.pdf"
        fig.savefig(os.path.join(outdir, fname_full))
        plt.close(fig)

    make_plot("displacement", r"$\log_{10}\delta\,[\mathrm{mm}]$", "displacement")
    make_plot("force", r"$\log_{10}|f_i|\,[\mathrm{N}]$", "force")
    make_plot("stress", r"$\log_{10}|\sigma_{ij}|\,[\mathrm{MPa}]$", "stress")


# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", required=True)
    parser.add_argument("--angle", required=True)
    parser.add_argument("--pkl_path", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    with open(args.pkl_path, "rb") as f:
        data = pickle.load(f)

    groups_by_b = defaultdict(dict)
    for k, v in data.items():
        groups_by_b[k[1]][k] = v

    os.makedirs(args.outdir, exist_ok=True)

    for b_value in sorted(groups_by_b):
        plot_group(
            select_items=groups_by_b[b_value],
            family=args.family,
            angle=args.angle,
            b_value=b_value,
            outdir=args.outdir,
        )


# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()
