"""
INCOIS Live Access Server / THREDDS adapter.

How to get URLs:
1. Open https://las.incois.gov.in/thredds/catalog.html
2. Navigate to a dataset (e.g. WAVEWATCH III wave forecast, ocean analysis)
3. Click the dataset -> copy the OPeNDAP URL (.html -> remove 'html', or use the dodsC link)
4. Put them in .env:
   INCOIS_OPENDAP_URLS={"temperature": "https://las.incois.gov.in/thredds/dodsC/....", "waves": "..."}
"""
import json
import xarray as xr
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import INCOIS_OPENDAP_URLS

# INCOIS variable names vary per dataset; map layer -> possible variable names
INCOIS_VARS = {
    "temperature": ["temp", "thetao", "temperature", "sst"],
    "salinity": ["sal", "so", "salinity", "sss"],
    "current_u": ["u", "uo", "cur_spd_u"],
    "current_v": ["v", "vo", "cur_spd_v"],
    "wave_height": ["hs", "swh", "wave_height", "VMDR"],  # WW3 names vary
    "wave_direction": ["dir", "wavedir", "VMDR_dir"],
    "wave_period": ["per", "mean_period", "VTPK"],
}


def fetch_layer(layer: str) -> xr.DataArray | None:
    url = INCOIS_OPENDAP_URLS.get(layer)
    if not url:
        return None
    try:
        ds = xr.open_dataset(url)  # OPeNDAP over dodsC
        candidates = INCOIS_VARS.get(layer, [])
        var = next((v for v in candidates if v in ds), None)
        if var is None:
            print(f"[incois] none of {candidates} in dataset vars={list(ds.data_vars)[:10]}")
            return None
        da = ds[var]
        da = da.rename({k: v for k, v in
                        {"longitude": "lon", "latitude": "lat", "depth": "depth"}.items()
                        if k in da.dims or k in da.coords})
        return da
    except Exception as e:
        print(f"[incois] {layer} failed: {e}")
        return None