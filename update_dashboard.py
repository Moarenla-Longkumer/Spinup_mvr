"""Bundle DayCent QA/QC outputs into the repo so they render on Streamlit Cloud.

Run this AFTER you have:
  1. regenerated the QA/QC outputs, and
  2. re-run the notebook's inventory-builder cell so qaqc_inventory.csv is fresh,
  3. copied that fresh qaqc_inventory.csv (with absolute /Users/... paths) into this folder.

What it does:
  - reads qaqc_inventory.csv
  - for every path column, copies the referenced file into assets/ (mirroring the
    site/check-folder structure) and rewrites the value to a relative assets/... path
  - removes the old assets/ first so deleted plots don't linger
  - leaves rows whose source file is missing pointing at a (non-existent) relative
    path, which the app shows gracefully as "not found"

Usage:
    python update_dashboard.py
"""

import csv
import shutil
import sys
from pathlib import Path

# Marker that separates the machine-specific prefix from the per-site structure.
# Everything after this marker becomes the path under assets/.
SITES_MARKER = "daycent_sites2/sites/"
ASSETS = Path("assets")
INV = Path("qaqc_spinup_inventory.csv")

# Columns in the CSV that hold filesystem paths we want to bundle.
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


def to_relative(value: str):
    """Map an absolute source path to (relative_assets_path, source_path).

    Returns (None, None) for empty values or paths that don't contain the sites
    marker (e.g. values that are already relative assets/ paths)."""
    value = (value or "").strip()
    if not value:
        return None, None
    idx = value.find(SITES_MARKER)
    if idx == -1:
        return None, None
    rel = value[idx + len(SITES_MARKER):]
    return (ASSETS / rel).as_posix(), Path(value)


def main():
    if not INV.exists():
        sys.exit(f"ERROR: {INV} not found. Copy the fresh inventory CSV here first.")

    raw = INV.read_text()
    if SITES_MARKER not in raw:
        sys.exit(
            "Nothing to do: qaqc_inventory.csv has no absolute source paths "
            f"(looking for '{SITES_MARKER}'). It is already relativized, or you "
            "need to copy in a freshly generated CSV from the notebook first."
        )

    # Safe to rebuild now that we know fresh source paths are present.
    # Start assets/ from scratch so removed plots disappear.
    if ASSETS.exists():
        shutil.rmtree(ASSETS)

    copied = missing = skipped = 0
    rows = []
    with INV.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            for col in PATH_COLS:
                if col not in row:
                    continue
                rel_path, src = to_relative(row[col])
                if rel_path is None:
                    skipped += 1
                    continue
                if src is not None and src.is_file():
                    dest = Path(rel_path)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    copied += 1
                else:
                    missing += 1
                row[col] = rel_path
            rows.append(row)

    with INV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. rows={len(rows)} copied={copied} missing={missing} skipped={skipped}")
    print("Next: git add -A && git commit -m 'Update QA/QC outputs' && git push")


if __name__ == "__main__":
    main()
