"""
Argo float data — ftp://ftp.ifremer.fr/ifremer/argo via the `argopy` library.
Falls back to ERDDAP automatically if FTP is blocked on your network.
"""
import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import ARGO_BACKEND, ARGO_BBOX


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def fetch_region(bbox: list[float] | None = None, max_profiles: int = 1500) -> dict:
    """Return float positions + latest T/S profiles in a region."""
    bbox = bbox or ARGO_BBOX
    lon0, lon1, lat0, lat1 = bbox
    import argopy
    try:
        argopy.set_options(src=ARGO_BACKEND)  # "ftp" or "erddap"
        f = argopy.DataFetcher(cache=True).region(
            [lon0, lon1, lat0, lat1, 0, 2000]
        )
        ds = f.to_xarray()
    except Exception as e:
        print(f"[argo] fetch failed ({ARGO_BACKEND}): {e}")
        # last-chance fallback
        try:
            argopy.set_options(src="erddap")
            ds = argopy.DataFetcher().region([lon0, lon1, lat0, lat1, 0, 2000]).to_xarray()
        except Exception as e2:
            print(f"[argo] erddap fallback also failed: {e2}")
            return {"floats": [], "source": "argo", "error": str(e2)}

    plat = np.array([str(p).strip() for p in ds["PLATFORM_NUMBER"].values])
    time = np.array(ds["TIME"].values, dtype="datetime64[s]").astype(str)
    latp = ds["LATITUDE"].values.astype(float)
    lonp = ds["LONGITUDE"].values.astype(float)
    pres = ds["PRES"].values.astype(float)
    temp = ds["TEMP"].values.astype(float)
    psal = ds["PSAL"].values.astype(float)

    # group by profile index (each row in N_PROF = one profile)
    floats: dict[str, dict] = {}
    n = len(plat)
    step = max(1, n // max_profiles)
    for i in range(0, n, step):
        pid = plat[i]
        if pid in ("", "nan"):
            continue
        rec = floats.setdefault(pid, {"platform": pid, "lat": float(latp[i]),
                                      "lon": float(lonp[i]), "time": time[i],
                                      "profiles": 0})
        rec["profiles"] += 1

    return {
        "bbox": {"lon": [lon0, lon1], "lat": [lat0, lat1]},
        "floats": list(floats.values()),
        "source": f"argo ({ARGO_BACKEND})",
    }


def nearest_profile(lat: float, lon: float, bbox=None) -> dict:
    """Depth profile (pressure/temp/salinity) from the closest Argo profile."""
    import argopy
    region = [lon - 3, lon + 3, lat - 3, lat + 3, 0, 2000]
    argopy.set_options(src=ARGO_BACKEND if ARGO_BACKEND else "erddap")
    ds = argopy.DataFetcher(cache=True).region(region).to_xarray()

    plat = np.array([str(p).strip() for p in ds["PLATFORM_NUMBER"].values])
    latp = ds["LATITUDE"].values.astype(float)
    lonp = ds["LONGITUDE"].values.astype(float)
    dist = _haversine(lat, lon, latp, lonp)
    idx = int(np.nanargmin(np.where(np.isnan(dist), 1e18, dist * (plat == plat[np.nanargmin(dist)]))))

    pres = ds["PRES"].values[idx]
    temp = ds["TEMP"].values[idx]
    psal = ds["PSAL"].values[idx]
    good = ~np.isnan(pres) & ~np.isnan(temp)
    order = np.argsort(pres[good])

    return {
        "requested": {"lat": lat, "lon": lon},
        "platform": plat[idx],
        "profile_lat": float(latp[idx]),
        "profile_lon": float(lonp[idx]),
        "distance_km": float(dist[idx]),
        "time": str(np.array(ds["TIME"].values[idx], dtype="datetime64[s]")),
        "pressure_dbar": pres[good][order].tolist(),
        "temperature_c": temp[good][order].tolist(),
        "salinity_psu": psal[good][order].tolist(),
        "source": f"argo ({ARGO_BACKEND})",
    }