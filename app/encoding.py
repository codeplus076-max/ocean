import numpy as np
import xarray as xr


def normalize_lon(da: xr.DataArray, lon_name="lon") -> xr.DataArray:
    """Convert 0..360 longitudes to -180..180 and sort."""
    da = da.sortby(lon_name)
    lons = da[lon_name].values.astype(float)
    if lons.max() > 180:
        da = da.assign_coords({lon_name: (((lons + 180) % 360) - 180)}).sortby(lon_name)
    return da


def nan_to_none(arr: np.ndarray):
    """Replace NaN with None so JSON gets null (frontend skips it)."""
    return np.where(np.isnan(arr), None, arr.astype(float)).tolist()


def field_payload(da: xr.DataArray, layer: str, units: str, source: str,
                  demo: bool, time_idx: int = -1, depth_idx: int | None = None,
                  stride: int = 1) -> dict:
    """Slice a (time, depth, lat, lon) DataArray into a 3D-friendly JSON payload."""
    da = normalize_lon(da)
    if "time" in da.dims:
        da = da.isel(time=time_idx)
    if depth_idx is not None and "depth" in da.dims:
        da = da.isel(depth=depth_idx)
        dims3d = False
    else:
        dims3d = "depth" in da.dims

    lon = da["lon"].values[::stride].tolist()
    lat = da["lat"].values[::stride].tolist()
    depth = da["depth"].values.tolist() if dims3d else [0.0]
    values = da.values[::stride] if not dims3d else da.values[:, ::stride, ::stride]

    return {
        "layer": layer,
        "units": units,
        "source": source,
        "demo": demo,
        "lon": lon,
        "lat": lat,
        "depth": depth,
        "data": nan_to_none(np.asarray(values, dtype=float)),
    }