"""Bundle DayCent QA/QC outputs into the repo so they render on Streamlit Cloud.

Run this AFTER you have:
  1. regenerated the QA/QC outputs, and
  2. re-run the notebook's inventory-builder cell so qaqc_inventory.csv is fresh,
  3. copied that fresh qaqc_inventory.csv (with absolute /Users/... paths) into this folder.

What it does:
  - reads qaqc_spinup_inventory.csv next to this script
  - for every path column, copies the referenced file into assets/ (mirroring the
    site/check-folder structure) and rewrites the value to a relative assets/... path
  - removes the old assets/ first so deleted plots don't linger
  - leaves rows whose source file is missing pointing at a (non-existent) relative
    path, which the app shows gracefully as "not found"

Usage (from any directory):
    python /path/to/Spinup_mvr/update_dashboard.py
    # or
    cd /path/to/Spinup_mvr && python update_dashboard.py
"""

import csv
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Marker that separates the machine-specific prefix from the per-site structure.
# Everything after this marker becomes the path under assets/.
SITES_MARKER = "daycent_sites2/sites/"
ASSETS = SCRIPT_DIR / "assets"
INV = SCRIPT_DIR / "qaqc_spinup_inventory.csv"
# Notebook output (absolute paths); used when Spinup_mvr inventory is already relativized.
SOURCE_INV = (
    SCRIPT_DIR.parent.parent.parent
    / "daycent_sites2"
    / "output_dashboard_files"
    / "qaqc_spinup_inventory.csv"
)

# Columns in the CSV that hold a single filesystem path to bundle.
PATH_COLS = [
    "site_dir",
    "somsc_summary",
    "biomass_summary",
    "n2o_summary",
    "somsc_spinup_png",
    "somsc_exp_png",
    "somsc_scatter_png",
    "biomass_scatter_png",
    "n2o_scatter_png",
]

# Columns that hold semicolon-separated lists of paths (e.g. livec_out plots).
PATH_LIST_COLS = [
    "biomass_livec_pngs",
]


def _rel_assets_path(site_relative: str) -> Path:
    """Path under Spinup_mvr/assets/ for a site-relative file."""
    return ASSETS / site_relative


def to_relative(value: str):
    """Map a source path to (inventory_relative_path, source_path).

    Returns (None, None) for empty values or paths that cannot be resolved.
    """
    value = (value or "").strip()
    if not value:
        return None, None

    idx = value.find(SITES_MARKER)
    if idx != -1:
        rel = value[idx + len(SITES_MARKER) :]
        dest = _rel_assets_path(rel)
        return dest.relative_to(SCRIPT_DIR).as_posix(), Path(value)

    path = Path(value)
    if not path.is_absolute():
        path = (SCRIPT_DIR / path).resolve()
    if path.is_file():
        try:
            rel = path.relative_to(SCRIPT_DIR)
        except ValueError:
            return None, None
        return rel.as_posix(), path

    return None, None


def copy_path(value: str):
    """Copy one file into assets/. Returns (relative_path, copied, missing)."""
    rel_path, src = to_relative(value)
    if rel_path is None:
        return None, 0, 0

    dest = (SCRIPT_DIR / rel_path).resolve()
    if src is not None and src.is_file():
        if src.resolve() == dest:
            return rel_path, 0, 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return rel_path, 1, 0
    return rel_path, 0, 1


def resolve_input_inventory() -> Path:
    """Pick an inventory CSV that still has absolute daycent_sites2 paths."""
    candidates = [INV, SOURCE_INV]
    for path in candidates:
        if path.exists() and SITES_MARKER in path.read_text(encoding="utf-8", errors="replace"):
            if path != INV:
                print(f"[INFO] {INV.name} is already relativized; using source inventory:")
                print(f"       {path}")
            return path

    if INV.exists():
        sys.exit(
            "Nothing to do: no inventory with absolute source paths was found.\n"
            f"  Checked: {INV}\n"
            f"  Checked: {SOURCE_INV}\n"
            "Re-run qaqc_dashboard.ipynb, or copy a fresh CSV into Spinup_mvr/."
        )
    sys.exit(f"ERROR: {INV} not found. Run qaqc_dashboard.ipynb first.")


def main():
    input_inv = resolve_input_inventory()

    if ASSETS.exists():
        shutil.rmtree(ASSETS)
    ASSETS.mkdir(parents=True, exist_ok=True)

    copied = missing = skipped = 0
    rows = []
    with input_inv.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            for col in PATH_COLS:
                if col not in row:
                    continue
                rel_path, did_copy, did_miss = copy_path(row[col])
                if rel_path is None:
                    skipped += 1
                    continue
                copied += did_copy
                missing += did_miss
                row[col] = rel_path

            for col in PATH_LIST_COLS:
                if col not in row:
                    continue
                path_values = [p.strip() for p in (row[col] or "").split(";") if p.strip()]
                if not path_values:
                    continue
                rel_paths = []
                for path_value in path_values:
                    rel_path, did_copy, did_miss = copy_path(path_value)
                    if rel_path is None:
                        skipped += 1
                        continue
                    copied += did_copy
                    missing += did_miss
                    rel_paths.append(rel_path)
                row[col] = ";".join(rel_paths)

            rows.append(row)

    with INV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. rows={len(rows)} copied={copied} missing={missing} skipped={skipped}")
    print(f"Assets: {ASSETS}")
    print("Next: git add -A && git commit -m 'Update QA/QC outputs' && git push")


if __name__ == "__main__":
    main()
