#!/usr/bin/env python3
"""
Script to extract Pakistan boundary from CMIP6 Daily Models and merge
historical and ssp245 into a single continuous time-series (1850-2100).

Grid File: regular_grid_pakistan.txt
Input:  /mnt/wcs-s2-d1/CMIP6_GCM/daily/<MODEL>/pr/<historical|ssp245>/*.nc
Output: /mnt/wcs-s2-d1/pk-boundaries/<MODEL>/ssp245/pr/pr_PAK_<MODEL>_r1i1p1f1_gn_day_1850-2100_ssp245.nc
"""

import os
import subprocess
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================
INPUT_BASE_DIR = Path("/mnt/wcs-s2-d1/CMIP6_GCM/daily")
OUTPUT_BASE_DIR = Path("/mnt/wcs-s2-d1/pk-boundaries")

# Grid definition file path (same directory as this script)
GRID_FILE = Path(__file__).parent / "regular_grid_pakistan.txt"

# 26 Selected Models
MODELS = [
    "ACCESS-ESM1-5", "AWI-ESM-1-REcoM", "BCC-CSM2-MR", "CAMS-CSM1-0",
    "CMCC-ESM2", "CNRM-CM6-1", "CanESM5", "EC-Earth3",
    "EC-Earth3-CC", "FGOALS-g3", "GFDL-CM4", "GFDL-ESM4",
    "HadGEM3-GC31-LL", "INM-CM4-8", "IPSL-CM6A-LR", "KACE-1-0-G",
    "KIOST-ESM", "MIROC6", "MPI-ESM1-2-HR", "MPI-ESM1-2-LR",
    "MRI-ESM2-0", "NESM3", "NorESM2-LM", "NorESM2-MM",
    "TaiESM1", "UKESM1-0-LL"
]

VARIABLE = "pr"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def load_grid_coordinates(grid_file: Path):
    """
    Parses CDO grid file and returns (lon_min, lon_max, lat_min, lat_max).
    """
    if not grid_file.exists():
        raise FileNotFoundError(f"Grid file not found: {grid_file}")

    params = {}
    with open(grid_file, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, val = line.split("=", 1)
                params[key.strip()] = val.strip()

    xfirst = float(params["xfirst"])
    xsize = int(params["xsize"])
    xinc = float(params.get("xinc", 1.0))
    xlast = xfirst + (xsize - 1) * xinc

    yfirst = float(params["yfirst"])
    ysize = int(params["ysize"])
    yinc = float(params.get("yinc", 1.0))
    ylast = yfirst + (ysize - 1) * yinc

    lon_min, lon_max = min(xfirst, xlast), max(xfirst, xlast)
    lat_min, lat_max = min(yfirst, ylast), max(yfirst, ylast)
    return lon_min, lon_max, lat_min, lat_max

# ==========================================
# PROCESSING FUNCTION
# ==========================================
def extract_and_merge_boundaries():
    lon_min, lon_max, lat_min, lat_max = load_grid_coordinates(GRID_FILE)

    print("=" * 75)
    print("CMIP6 Pakistan Boundary Extraction & Historical + SSP245 Merging")
    print(f"Grid Source:      {GRID_FILE.name}")
    print(f"Bounding Box:     Lon [{lon_min} to {lon_max}], Lat [{lat_min} to {lat_max}]")
    print(f"Input Base Dir:   {INPUT_BASE_DIR}")
    print(f"Output Base Dir:  {OUTPUT_BASE_DIR}")
    print("=" * 75)

    processed_count = 0
    skipped_count = 0
    failed_models = []

    for model in MODELS:
        print(f"\n>>> Processing Model: {model}")

        hist_dir = INPUT_BASE_DIR / model / VARIABLE / "historical"
        ssp_dir = INPUT_BASE_DIR / model / VARIABLE / "ssp245"

        # Check folders exist
        if not hist_dir.exists() or not ssp_dir.exists():
            print(f"  [SKIPPED] Missing folder(s):")
            if not hist_dir.exists():
                print(f"    - Historical not found: {hist_dir}")
            if not ssp_dir.exists():
                print(f"    - SSP245 not found:     {ssp_dir}")
            continue

        hist_files = sorted(list(hist_dir.glob("*.nc")))
        ssp_files = sorted(list(ssp_dir.glob("*.nc")))

        if not hist_files or not ssp_files:
            print(f"  [SKIPPED] Missing NetCDF files:")
            if not hist_files:
                print(f"    - No historical .nc files found in {hist_dir}")
            if not ssp_files:
                print(f"    - No ssp245 .nc files found in {ssp_dir}")
            continue

        # Combine all historical followed by ssp245
        all_files = hist_files + ssp_files
        print(f"  Found {len(hist_files)} historical files and {len(ssp_files)} ssp245 files ({len(all_files)} total).")

        # Destination folder: model -> ssp245 -> pr
        output_dir = OUTPUT_BASE_DIR / model / "ssp245" / VARIABLE
        output_dir.mkdir(parents=True, exist_ok=True)

        # Exact filename format with only model name changing
        out_filename = f"pr_PAK_{model}_r1i1p1f1_gn_day_1850-2100_ssp245.nc"
        out_file = output_dir / out_filename

        # Skip if already exists and non-empty
        if out_file.exists() and out_file.stat().st_size > 0:
            print(f"  [ALREADY EXISTS] Skipping: {out_filename}")
            skipped_count += 1
            continue

        # Temporary file for atomic writing
        temp_out_file = out_file.with_name(f"{out_file.name}.tmp")

        # CDO command: merge along time axis and extract Pakistan boundary
        cdo_cmd = [
            "cdo",
            "-s",
            f"-sellonlatbox,{lon_min},{lon_max},{lat_min},{lat_max}",
            "-mergetime",
            *[str(f) for f in all_files],
            str(temp_out_file)
        ]

        print(f"  Merging & Extracting -> {out_filename} ...")

        try:
            subprocess.run(
                cdo_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            # Atomically replace .tmp with final .nc
            temp_out_file.replace(out_file)
            processed_count += 1
            print(f"  [OK] Successfully created: {out_filename}")

        except subprocess.CalledProcessError as e:
            if temp_out_file.exists():
                temp_out_file.unlink()
            err_msg = e.stderr.strip()
            print(f"  [FAILED] Model: {model}")
            print(f"    CDO Error: {err_msg}")
            failed_models.append((model, err_msg))

    print("\n" + "=" * 75)
    print("EXTRACTION & MERGE SUMMARY:")
    print(f"Models Successfully Processed: {processed_count}")
    print(f"Models Skipped (Already done): {skipped_count}")
    print(f"Models Failed:                 {len(failed_models)}")

    if failed_models:
        print("\nFailed Model Details:")
        for m, err in failed_models:
            print(f"- {m}: {err}")
    print("=" * 75)

if __name__ == "__main__":
    extract_and_merge_boundaries()
