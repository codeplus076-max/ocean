import asyncio
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from config import DEFAULT_STRIDE, LAYERS
from app.encoding import field_payload, nan_to_none
from app.services.store import store, _subscribers
from app.adapters import waves, argo, glider
from app.cache import cache

router = APIRouter(prefix="/api")


# ---------------- meta & health ----------------
@router.get("/health")
async def health():
    return {"status": "ok", "version": store.version,
            "layers_loaded": list(store.fields.keys())}


@router.get("/meta")
async def meta():
    layers = {}
    for name, cfg in LAYERS.items():
        m = store.meta.get(name, {})
        layers[name] = {"label": cfg["label"], "units": cfg["units"],
                        "source": m.get("source"), "demo": m.get("demo", True),
                        "available": name in store.fields}
    return {"layers": layers,
            "argo_floats": len(store.argo_index.get("floats", [])),
            "glider_missions": len(store.glider_index.get("missions", [])),
            "version": store.version}


# ---------------- gridded fields (3D volumes) ----------------
@router.get("/field/{layer}")
async def get_field(layer: str,
                    stride: int = Query(DEFAULT_STRIDE, ge=1, le=10),
                    depth_index: int | None = Query(None, ge=0),
                    time_index: int = Query(-1)):
    if layer not in store.fields:
        raise HTTPException(404, f"layer '{layer}' not loaded. See /api/meta")
    da = store.fields[layer]
    units = LAYERS.get(layer, {}).get("units", "")
    src = store.meta.get(layer, {})
    return field_payload(da, layer, units, src.get("source", "?"),
                         src.get("demo", True), time_idx=time_index,
                         depth_idx=depth_index, stride=stride)


@router.get("/currents")
async def get_currents(stride: int = Query(DEFAULT_STRIDE, ge=1, le=10),
                       depth_index: int = Query(0, ge=0)):
    """u/v components + speed/direction — ready for arrow/vector rendering."""
    if "current_u" not in store.fields or "current_v" not in store.fields:
        raise HTTPException(404, "currents not loaded")
    u = store.fields["current_u"].isel(depth=depth_index)
    v = store.fields["current_v"].isel(depth=depth_index)
    lon = u["lon"].values[::stride].tolist()
    lat = u["lat"].values[::stride].tolist()
    uu = u.values[::stride]
    vv = v.values[::stride]
    speed = np.sqrt(uu ** 2 + vv ** 2)
    direc = (np.degrees(np.arctan2(vv, uu)) + 360) % 360
    return {"lon": lon, "lat": lat,
            "u": nan_to_none(uu), "v": nan_to_none(vv),
            "speed": nan_to_none(speed), "direction_deg": nan_to_none(direc),
            "units": "m/s", "demo": store.meta.get("current_u", {}).get("demo", True)}


# ---------------- waves ----------------
@router.get("/waves/point")
async def waves_point(lat: float, lon: float):
    key = f"wave:{lat:.2f}:{lon:.2f}"
    if (hit := cache.get(key)) is not None:
        return hit
    data = await waves.waves_point(lat, lon)
    cache.set(key, data)
    return data


@router.get("/waves/field")
async def waves_field():
    if (hit := cache.get("wave_field")) is not None:
        return hit
    data = await waves.waves_field()
    cache.set("wave_field", data)
    return data


# ---------------- Argo ----------------
@router.get("/argo/floats")
async def argo_floats():
    return store.argo_index


@router.get("/argo/profile")
async def argo_profile(lat: float, lon: float):
    key = f"argo:{lat:.2f}:{lon:.2f}"
    if (hit := cache.get(key)) is not None:
        return hit
    try:
        data = await asyncio.to_thread(argo.nearest_profile, lat, lon)
    except Exception as e:
        raise HTTPException(502, f"Argo lookup failed: {e}")
    cache.set(key, data)
    return data


# ---------------- Gliders ----------------
@router.get("/gliders")
async def gliders():
    return store.glider_index


@router.get("/gliders/tracks")
async def glider_tracks(lat_min: float = -40, lat_max: float = 30,
                        lon_min: float = 30, lon_max: float = 110):
    return await asyncio.to_thread(
        glider.erddap_tracks, lat_min, lat_max, lon_min, lon_max)


# ---------------- point sampling & timeseries ----------------
@router.get("/timeseries/{layer}")
async def timeseries(layer: str, lat: float, lon: float):
    if layer not in store.fields:
        raise HTTPException(404, f"layer '{layer}' not loaded")
    da = store.fields[layer]
    da = da.sel(lat=lat, lon=lon, method="nearest")
    if "depth" in da.dims:
        da = da.isel(depth=0)
    return {"layer": layer,
            "nearest": {"lat": float(da["lat"]), "lon": float(da["lon"])},
            "time": [str(t) for t in da["time"].values],
            "values": nan_to_none(da.values.astype(float)),
            "units": LAYERS.get(layer, {}).get("units", "")}


# ---------------- WebSocket (live push on refresh) ----------------
@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _subscribers.add(ws)
    try:
        await ws.send_json({"type": "hello", "version": store.version})
        while True:
            msg = await ws.receive_text()  # keepalive / ignore content
            if msg == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        _subscribers.discard(ws)

@router.get("/briefing")
async def briefing(lat: float, lon: float, radius_deg: float = 3.0):
    """All real data for one location, in a single JSON response."""
    out = {"requested": {"lat": lat, "lon": lon}, "sources": {}, "errors": {}}
    try:
        prof = await asyncio.to_thread(argo.nearest_profile, lat, lon)
        out["argo_profile"] = prof
    except Exception as e:
        out["argo_profile"] = None
        out["errors"]["profile"] = str(e)[:200]

    def _grid():
        res = {}
        for layer in ("temperature","salinity","current_u","current_v","ssh"):
            da = store.fields.get(layer)
            if da is None: continue
            try:
                d0 = da.isel(depth=0) if "depth" in da.dims else da
                if "time" in d0.dims: d0 = d0.isel(time=-1)
                p = d0.sel(lat=lat, lon=lon, method="nearest")
                val = float(p.values)
                res[layer] = {"value": None if np.isnan(val) else round(val,4),
                              "demo": bool(store.meta.get(layer,{}).get("demo",True))}
            except Exception as e: print(f"[briefing] {layer}: {e}")
        return res
    out["grid"] = await asyncio.to_thread(_grid)

    try:
        out["waves"] = await waves.waves_point(lat, lon)
    except Exception as e:
        out["waves"] = None; out["errors"]["waves"] = str(e)[:200]

    nearby = [f for f in store.argo_index.get("floats", [])
              if abs(f["lat"]-lat) < radius_deg*1.4 and abs(f["lon"]-lon) < radius_deg]
    nearby.sort(key=lambda f: (f["lat"]-lat)**2 + (f["lon"]-lon)**2)
    out["floats"] = nearby[:10]
    return out