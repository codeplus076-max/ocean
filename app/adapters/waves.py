"""
Wave data. Primary: INCOIS (if you configured it) — handled in the store.
This adapter uses Open-Meteo Marine API (free, no API key) which serves
CMEMS wave model output — perfect for point forecasts + a global field snapshot.
"""
import httpx
import numpy as np

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

WAVE_PARAMS = "wave_height,wave_direction,wave_period,sea_surface_temperature"


async def waves_point(lat: float, lon: float, days: int = 5) -> dict:
    params = dict(
        latitude=lat, longitude=lon,
        hourly=WAVE_PARAMS,
        forecast_days=days, past_days=1,
        timezone="UTC",
    )
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(MARINE_URL, params=params)
        r.raise_for_status()
        d = r.json()
    h = d.get("hourly", {})
    return {
        "lat": lat, "lon": lon,
        "time": h.get("time", []),
        "wave_height_m": h.get("wave_height", []),
        "wave_direction_deg": h.get("wave_direction", []),
        "wave_period_s": h.get("wave_period", []),
        "sst_c": h.get("sea_surface_temperature", []),
        "source": "open-meteo/marine (CMEMS wave model)",
    }


async def waves_field(nlat: int = 10, nlon: int = 20) -> dict:
    """Coarse global snapshot of significant wave height for the 3D globe."""
    lats = np.linspace(-75, 75, nlat)
    lons = np.linspace(-180, 180, nlon)
    grid_lats, grid_lons = np.meshgrid(lats, lons, indexing="ij")
    # open-meteo accepts comma-separated coordinate lists
    lat_q = ",".join(f"{v:.2f}" for v in grid_lats.ravel())
    lon_q = ",".join(f"{v:.2f}" for v in grid_lons.ravel())
    params = dict(latitude=lat_q, longitude=lon_q,
                  hourly="wave_height", forecast_days=1, timezone="UTC")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(MARINE_URL, params=params)
        r.raise_for_status()
        results = r.json() if isinstance(r.json(), list) else [r.json()]

    field = np.full((nlat, nlon), np.nan)
    latest = []
    for i, res in enumerate(results):
        h = res.get("hourly", {}).get("wave_height", [])
        if not h:
            continue
        # take the value nearest "now" that is not None
        val = next((v for v in reversed(h) if v is not None), None)
        row, col = divmod(i, nlon)
        if val is not None:
            field[row, col] = val
            latest.append({"lat": grid_lats[row, col], "lon": grid_lons[row, col],
                           "wave_height_m": val})
    return {
        "lon": lons.tolist(), "lat": lats.tolist(),
        "wave_height_m": np.where(np.isnan(field), None, field).tolist(),
        "points": latest,
        "source": "open-meteo/marine",
    }