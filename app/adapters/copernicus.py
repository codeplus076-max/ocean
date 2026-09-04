"""
Copernicus Marine — GLOBAL_MULTIYEAR_PHY_001_030 (reanalysis).
Variables: thetao (temp), so (salinity), uo/vo (currents), zos (sea surface height).
Requires free account -> set CMEMS_USERNAME / CMEMS_PASSWORD in .env
Browse dataset ids with: copernicusmarine describe --include-datasets
"""
import os
import xarray as xr
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import CMEMS_USERNAME, CMEMS_PASSWORD, CMEMS_DATASET_ID, DEFAULT_BBOX, LAYERS


def _auth():
    if CMEMS_USERNAME and CMEMS_PASSWORD:
        os.environ["COPERNICUSMARINE_SERVICE_USERNAME"] = CMEMS_USERNAME
        os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"] = CMEMS_PASSWORD


def fetch_layers(layers: list[str] | None = None) -> dict[str, xr.DataArray] | None:
    """Download the latest window of all requested layers in ONE request."""
        # Do not attempt login or download when credentials are missing.
    # This prevents copernicusmarine from opening an interactive prompt.
    if not CMEMS_USERNAME or not CMEMS_PASSWORD:
        print("[copernicus] credentials not configured - using fallback/demo data")
        return None
    _auth()
    try:
        import copernicusmarine
    except ImportError:
        print("[copernicus] library not installed")
        return None

    if layers is None:
        layers = list(LAYERS.keys())
    variables = [LAYERS[l]["cmems_var"] for l in layers]

    end = datetime.utcnow()
    start = end - timedelta(days=10)
    try:
        ds = copernicusmarine.open_dataset(
            dataset_id=CMEMS_DATASET_ID,
            minimum_longitude=DEFAULT_BBOX["min_lon"],
            maximum_longitude=DEFAULT_BBOX["max_lon"],
            minimum_latitude=DEFAULT_BBOX["min_lat"],
            maximum_latitude=DEFAULT_BBOX["max_lat"],
            minimum_depth=DEFAULT_BBOX["min_depth"],
            maximum_depth=DEFAULT_BBOX["max_depth"],
            start_datetime=start,
            end_datetime=end,
            variables=variables,
        )
    except Exception as e:
        print(f"[copernicus] fetch failed: {e}")
        return None

    rename = {LAYERS[l]["cmems_var"]: l for l in layers if LAYERS[l]["cmems_var"] in ds}
    ds = ds.rename(rename)

    out = {}
    for layer in layers:
        if layer in ds:
            da = ds[layer]
            # normalize coord names
            da = da.rename({
                "longitude": "lon", "latitude": "lat", **({"depth": "depth"} if "depth" in da.dims else {})
            })
            out[layer] = da
    return out or None