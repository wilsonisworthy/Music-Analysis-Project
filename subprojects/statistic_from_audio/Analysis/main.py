"""Analysis: load a CSV produced by csv_export and plot every metric
(attack time, decay time, brightness change) against dynamic/force level
at once -- one thin line per note (colored by octave) so each note's own
trajectory across pp/mf/ff is visible, plus an overall linear fit and
Pearson correlation per metric as a first-pass "equation" for how each
property responds to strike force."""

import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

DYNAMIC_ORDER = {"pp": 0, "p": 1, "mp": 2, "mf": 3, "f": 4, "ff": 5}


def _find_project_root(start):
    for parent in (start, *start.parents):
        if (parent / "main.py").exists() and (parent / "subprojects").exists():
            return parent
    raise RuntimeError("Could not find the project root (expected main.py + subprojects/ nearby)")


_PROJECT_ROOT = _find_project_root(Path(__file__).resolve())
_RESULTS_DIR = _PROJECT_ROOT / "Results"

sys.path.insert(0, str(_PROJECT_ROOT))
from main import choose  # reuse the router's own menu


def select_csv():
    if not _RESULTS_DIR.is_dir():
        print(f"No '{_RESULTS_DIR.name}/' folder found at {_PROJECT_ROOT}.")
        print("Run csv_export first to generate one.")
        sys.exit(1)
    csvs = sorted(_RESULTS_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csvs:
        print(f"No .csv files found in {_RESULTS_DIR.relative_to(_PROJECT_ROOT)}. Run csv_export first.")
        sys.exit(1)
    if len(csvs) == 1:
        return csvs[0]

    labels = [f"{p.name}" for p in csvs]
    result = choose("Pick a CSV to analyze (most recent first)", labels)
    if not isinstance(result, int):
        sys.exit(0)
    return csvs[result]


def load_rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    path = select_csv()
    rows = load_rows(path)
    print(f"Loaded {len(rows)} rows from {path.relative_to(_PROJECT_ROOT)}")

    groups_present = sorted({r["group"] for r in rows if r.get("group")})
    if len(groups_present) < 2:
        print("Only one dynamic/group present in this CSV -- need at least two "
              "(e.g. pp and ff) to show a force trend. Run csv_export against a "
              "folder that covers multiple dynamics instead.")
        return

    ordered_groups = sorted(groups_present, key=lambda g: DYNAMIC_ORDER.get(g.lower(), 99))
    group_rank = {g: i for i, g in enumerate(ordered_groups)}
    print(f"Dynamic levels found, softest to loudest: {', '.join(ordered_groups)}")
    print("(pp/mf/ff are 3 discrete categorical force levels, not a continuous")
    print(" velocity measurement -- treat trend shapes as suggestive, not precise.)\n")

    metrics = [
        ("attack_time_s", "Attack time (s)"),
        ("decay_time_s", "Decay time (s)"),
        ("brightness_change_pct", "Brightness change (%)"),
    ]

    # One entry per (note, octave), holding that note's row for each group,
    # so each note's own trajectory across dynamics can be drawn as a line.
    notes = {}
    for r in rows:
        key = (r.get("note", ""), r.get("octave", ""))
        notes.setdefault(key, {})[r["group"]] = r

    octaves = sorted({o for _, o in notes if o not in (None, "")}, key=int)
    cmap = plt.get_cmap("viridis", max(len(octaves), 1))
    octave_color = {o: cmap(i) for i, o in enumerate(octaves)}

    fig, axes = plt.subplots(1, len(metrics), figsize=(6 * len(metrics), 5))
    x_labels = ordered_groups
    x_positions = [group_rank[g] for g in x_labels]

    for ax, (col, title) in zip(axes, metrics):
        all_x, all_y = [], []
        for (note, octave), by_group in notes.items():
            xs, ys = [], []
            for g in x_labels:
                r = by_group.get(g)
                v = to_float(r.get(col)) if r else None
                if v is not None:
                    xs.append(group_rank[g])
                    ys.append(v)
            if len(xs) >= 2:
                ax.plot(xs, ys, color=octave_color.get(octave, "gray"), alpha=0.35, linewidth=1)
            all_x.extend(xs)
            all_y.extend(ys)

        if len(all_x) >= 2:
            x_arr, y_arr = np.array(all_x, dtype=float), np.array(all_y, dtype=float)
            slope, intercept = np.polyfit(x_arr, y_arr, 1)
            r = np.corrcoef(x_arr, y_arr)[0, 1]
            fit_x = np.array([min(x_positions), max(x_positions)], dtype=float)
            ax.plot(fit_x, slope * fit_x + intercept, color="black", linewidth=2.5,
                     linestyle="--", label=f"y = {slope:.3g}x + {intercept:.3g}\nr = {r:.2f}")
            ax.legend(fontsize=8, loc="best")
            print(f"{title}: n={len(all_x)}, Pearson r={r:.3f}, fit y = {slope:.4g}*x + {intercept:.4g}")
        else:
            print(f"{title}: not enough data points to fit a trend.")

        ax.set_xticks(x_positions)
        ax.set_xticklabels(x_labels)
        ax.set_xlabel("Dynamic level (force proxy)")
        ax.set_ylabel(title)
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.3)

    if octaves:
        handles = [plt.Line2D([0], [0], color=octave_color[o], lw=2, label=f"octave {o}") for o in octaves]
        fig.legend(handles=handles, loc="lower center", ncol=len(octaves), fontsize=8, bbox_to_anchor=(0.5, -0.02))

    fig.suptitle(f"{path.name} — {len(notes)} notes x {len(x_labels)} dynamics", fontsize=11)
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.show()


if __name__ == "__main__":
    main()
