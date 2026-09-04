import numpy as np
import pandas as pd
import xarray as xr


def _coords(nlat=91, nlon=181, times=8):
    lat = np.linspace(-80, 80, nlat, dtype=np.float32)
    lon = np.linspace(-180, 180, nlon, dtype=np.float32)
    depth = np.array([0, 50, 200, 700, 2000], dtype=np.float32)
    time = pd.date_range(pd.Timestamp.utcnow().floor("D"), periods=times, freq="12h")
    return time, depth, lat, lon


def _dataset(builder) -> xr.DataArray:
    time, depth, lat, lon = _coords()
    LON, LAT, Z = np.meshgrid(lon, lat, depth, indexing="ij")
    # shape -> (lon, depth, lat); transpose to (time, depth, lat, lon) below
    data = builder(LON.T, LAT.T, Z.T)  # (depth, lat, lon)
    data = data[np.newaxis].repeat(len(time), axis=0)
    # slow evolution so animation looks alive
    t = np.arange(len(time))[:, None, None, None]
    data = data + 0.15 * t * np.sin(LAT.T)[None]
    return xr.DataArray(
        data.astype(np.float32),
        coords={"time": time, "depth": depth, "lat": lat, "lon": lon},
        dims=("time", "depth", "lat", "lon"),
    )


def demo_temperature() -> xr.DataArray:
    def f(LON, LAT, Z):
        sst = 28.5 * np.cos(np.deg2rad(LAT)) ** 1.5 + 2.0 * np.sin(np.deg2rad(LON / 2))
        return sst * np.exp(-Z / 450.0) + 3.5
    return _dataset(f)


def demo_salinity() -> xr.DataArray:
    def f(LON, LAT, Z):
        base = 34.6 + 0.9 * np.exp(-((LAT - 15) / 22) ** 2)
        return base + 0.6 * np.exp(-Z / 200.0) - 0.3 * np.sin(np.deg2rad(LON))
    return _dataset(f)


def demo_ssh() -> xr.DataArray:
    def f(LON, LAT, Z):
        return 0.35 * np.sin(np.deg2rad(LON / 1.5)) * np.cos(np.deg2rad(LAT / 1.2)) + 0.1
    return _dataset(f)


def demo_currents() -> tuple[xr.DataArray, xr.DataArray]:
    def u(LON, LAT, Z):
        # western boundary jet + equatorial currents + gyre swirl
        jet = 1.4 * np.exp(-((LAT - 8) / 3) ** 2) * np.exp(-Z / 300)
        gyre = 0.6 * np.cos(np.deg2rad(LAT / 2)) * np.sin(np.deg2rad(LON / 3))
        return jet + gyre

    def v(LON, LAT, Z):
        gyre = 0.6 * np.sin(np.deg2rad(LAT / 2)) * np.cos(np.deg2rad(LON / 3))
        eq = 0.5 * np.exp(-((LAT) / 2.5) ** 2) * np.exp(-Z / 300)
        return gyre + eq
    return _dataset(u), _dataset(v)