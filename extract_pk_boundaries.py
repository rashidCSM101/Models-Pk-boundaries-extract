#!/usr/bin/env python3
"""
Script to extract Pakistan boundary from CMIP6 Daily Models using CDO
Coordinates: Lon [60.5, 82.5], Lat [23.5, 37.5]
Input:  /mnt/wcs-s2-d1/CMIP6_GCM/daily/<MODEL>/pr/<historical|ssp245>/*.nc
Output: /mnt/wcs-s2-d1/pk-boundaries/<MODEL>/pr/<historical|ssp245>/*.nc
"""

import os
import subprocess
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================
INPUT_BASE_DIR = Path("/mnt/wcs-s2-d1/CMIP6_GCM/daily")
OUTPUT_BASE_DIR = Path("/mnt/wcs-s2-d1/pk-boundaries")  # Destination folder

# Pakistan Specified Bounding Box (lon1, lon2, lat1, lat2)
LON_MIN, LON_MAX = 60.5, 82.5
LAT_MIN, LAT_MAX = 23.5, 37.5

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

SCENARIOS = ["historical", "ssp245"]
VARIABLE = "pr"

# ==========================================
# PROCESSING FUNCTION
# ==========================================
def extract_boundaries():
    print("=" * 70)
    print("Starting Pakistan Boundary Extraction with CDO")
    print(f"Bounding Box: Lon [{LON_MIN} to {LON_MAX}], Lat [{LAT_MIN} to {LAT_MAX}]")
    print(f"Input Directory:  {INPUT_BASE_DIR}")
    print(f"Output Directory: {OUTPUT_BASE_DIR}")
    print("=" * 70)

    failed_files = []
    processed_count = 0
    skipped_count = 0

    for model in MODELS:
        print(f"\n>>> Processing Model: {model}")

        for scenario in SCENARIOS:
            input_dir = INPUT_BASE_DIR / model / VARIABLE / scenario
            output_dir = OUTPUT_BASE_DIR / model / VARIABLE / scenario

            if not input_dir.exists():
                print(f"  [MISSING FOLDER] {input_dir}")
                continue

            # Output directory banayein
            output_dir.mkdir(parents=True, exist_ok=True)

            # NetCDF files search karein
            nc_files = sorted(list(input_dir.glob("*.nc")))

            if not nc_files:
                print(f"  [NO NC FILES] {input_dir}")
                continue

            print(f"  Scenario: {scenario} ({len(nc_files)} files found)")

            for nc_file in nc_files:
                out_file = output_dir / nc_file.name

                # Agar file already process ho chuki hai toh skip karein
                if out_file.exists() and out_file.stat().st_size > 0:
                    skipped_count += 1
                    continue

                # CDO command
                cdo_cmd = [
                    "cdo",
                    f"-sellonlatbox,{LON_MIN},{LON_MAX},{LAT_MIN},{LAT_MAX}",
                    str(nc_file),
                    str(out_file)
                ]

                try:
                    result = subprocess.run(
                        cdo_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True
                    )
                    processed_count += 1
                    print(f"    [OK] Extracted: {nc_file.name}")

                except subprocess.CalledProcessError as e:
                    if out_file.exists():
                        out_file.unlink()
                    print(f"    [FAILED] {nc_file.name}")
                    print(f"      CDO Error: {e.stderr.strip()}")
                    failed_files.append((str(nc_file), e.stderr.strip()))

    print("\n" + "=" * 70)
    print("EXTRACTION SUMMARY:")
    print(f"Total Files Extracted: {processed_count}")
    print(f"Total Files Skipped (Already existed): {skipped_count}")
    print(f"Total Failed Files: {len(failed_files)}")

    if failed_files:
        print("\nFailed Files Details:")
        for f, err in failed_files:
            print(f"- File: {f}\n  Error: {err}\n")
    print("=" * 70)

if __name__ == "__main__":
    extract_boundaries()
