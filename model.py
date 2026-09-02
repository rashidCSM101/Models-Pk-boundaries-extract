#!/usr/bin/env python3
"""
Automated CMIP6 Daily Precipitation (pr) Downloader using ESGF REST API.
Uses pure Python (requests) - Works seamlessly on Windows & Linux.
"""

import os
import sys
import requests
import urllib3
from pathlib import Path

# SSL warnings ko suppress karne ke liye
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# CONFIGURATION
# ==========================================
# Agar Windows par hi download karna hai toh apna local path de sakte hain (e.g., Path("E:/CMIP6_Data") ya Path("./downloaded_data"))
# Agar Linux server par chalana hai toh Path("/mnt/wcs-s2-d1/CMIP6_GCM/daily") rehne dein
BASE_DIR = Path("./downloaded_data")  # <--- Yahan apni marzi ka path rakhein

# 9 Missing Models
MODELS = [
    "ACCESS-CM2",
    "CESM2",
    "CESM2-WACCM",
    "CNRM-ESM2-1",
    "E3SM-2-0",
    "EC-Earth3-Veg",
    "EC-Earth3-Veg-LR",
    "HadGEM3-GC31-MM",
    "MIROC-ES2L"
]

SCENARIOS = ["historical", "ssp245"]
VARIABLE = "pr"
FREQUENCY = "day"

# ESGF Index Node Search URL
ESGF_SEARCH_URL = "https://esgf-node.llnl.gov/esg-search/search"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_download_urls(model, scenario):
    """ESGF API se files ki list aur direct download URLs fetch karta hai"""
    params = {
        "project": "CMIP6",
        "source_id": model,
        "experiment_id": scenario,
        "variable_id": VARIABLE,
        "frequency": FREQUENCY,
        "type": "File",
        "format": "application/solr+json",
        "limit": 1000
    }

    try:
        resp = requests.get(ESGF_SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"    [API Error] Could not query ESGF for {model} - {scenario}: {e}")
        return []

    docs = data.get("response", {}).get("docs", [])
    if not docs:
        return []

    variants = sorted(list(set(doc.get("variant_label", [""])[0] for doc in docs if "variant_label" in doc)))
    chosen_variant = "r1i1p1f1" if "r1i1p1f1" in variants else variants[0]

    files_to_download = []
    for doc in docs:
        if doc.get("variant_label", [""])[0] != chosen_variant:
            continue

        filename = doc.get("title")
        urls = doc.get("url", [])
        
        http_url = None
        for u in urls:
            parts = u.split("|")
            if len(parts) >= 3 and parts[2] == "HTTPServer":
                http_url = parts[0]
                break
        
        if http_url and filename:
            files_to_download.append((filename, http_url))

    files_to_download.sort(key=lambda x: x[0])
    return files_to_download


def download_file(url, out_path):
    """Pure Python streaming download with progress bar and resume capability"""
    temp_path = out_path.with_suffix(out_path.suffix + ".part")
    
    headers = {}
    downloaded = 0
    if temp_path.exists():
        downloaded = temp_path.stat().st_size
        headers["Range"] = f"bytes={downloaded}-"

    with requests.get(url, headers=headers, stream=True, verify=False, timeout=60) as r:
        if r.status_code in [200, 206]:
            total_size = int(r.headers.get("content-length", 0)) + downloaded
            mode = "ab" if downloaded > 0 else "wb"
            
            chunk_size = 1024 * 1024  # 1 MB chunk
            current = downloaded
            
            with open(temp_path, mode) as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        current += len(chunk)
                        mb_done = current / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024) if total_size else 0
                        pct = (current / total_size * 100) if total_size else 0
                        print(f"\r      Progress: {mb_done:.1f} MB / {mb_total:.1f} MB ({pct:.1f}%)", end="", flush=True)
            
            print()  # New line after completion
            temp_path.rename(out_path)
            return True
        else:
            print(f"\n      [HTTP Error] Server returned status code: {r.status_code}")
            return False


def download_models():
    print("=" * 70)
    print("CMIP6 Automated Batch Downloader (Python Native)")
    print(f"Target Directory: {BASE_DIR.resolve()}")
    print(f"Models Count: {len(MODELS)}")
    print(f"Scenarios: {SCENARIOS}")
    print("=" * 70)

    for model in MODELS:
        print(f"\n==========================================")
        print(f">>> Model: {model}")
        print(f"==========================================")

        for scenario in SCENARIOS:
            target_dir = BASE_DIR / model / VARIABLE / scenario
            target_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n  [Querying ESGF API] {model} -> {scenario} ...")
            files = get_download_urls(model, scenario)

            if not files:
                print(f"  [NOT FOUND] No files found for {model} - {scenario} on ESGF!")
                continue

            print(f"  [FOUND] {len(files)} files found. Target: {target_dir}")

            for filename, url in files:
                out_path = target_dir / filename

                # Agar file already complete download ho chuki ho
                if out_path.exists() and out_path.stat().st_size > 1024 * 1024:
                    print(f"    [ALREADY EXISTS] {filename}")
                    continue

                print(f"    [DOWNLOADING] {filename}")
                try:
                    success = download_file(url, out_path)
                    if success:
                        print(f"    [COMPLETED] {filename}")
                    else:
                        print(f"    [FAILED] {filename}")
                except Exception as e:
                    print(f"\n    [ERROR] {filename}: {e}")

    print("\n" + "=" * 70)
    print("All tasks finished!")
    print("=" * 70)


if __name__ == "__main__":
    download_models()
