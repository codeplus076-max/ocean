"""In-memory data store, refreshed on a schedule. Frontend always reads from here (fast)."""
import asyncio
import numpy as np
import xarray as xr
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from config import LAYERS
from app import demo
from app.adapters import copernicus, incois, waves, argo, glider


class OceanStore:
    def __init__(self):
        self.fields: dict[str, xr.DataArray] = {}
        self.meta: dict[str, dict] = {}
        self.argo_index: dict = {"floats": []}
        self.glider_index: dict = {"missions": []}
        self.version = 0  # bump on refresh -> WebSocket clients know to refetch

    # ---------- layer loading with fallback chain ----------
    def _set_layer(self, layer, da: xr.DataArray, source: str, is_demo: bool):
        self.fields[layer] = da
        self.meta[layer] = {"source": source, "demo": is_demo,
                            "units": LAYERS.get(layer, {}).get("units", "")}

    def load_layers(self):
        cmems = None
        if any(v in ("temperature", "salinity", "current_u", "current_v", "ssh")
               for v in LAYERS):
            cmems = copernicus.fetch_layers()

        for layer in LAYERS:
            if cmems and layer in cmems:
                self._set_layer(layer, cmems[layer], "copernicus-marine", False)
                continue
            da = incois.fetch_layer(layer)
            if da is not None:
                self._set_layer(layer, da, "incois", False)
                continue
            # demo fallback
            if layer == "temperature":
                self._set_layer(layer, demo.demo_temperature(), "demo", True)
            elif layer == "salinity":
                self._set_layer(layer, demo.demo_salinity(), "demo", True)
            elif layer == "ssh":
                self._set_layer(layer, demo.demo_ssh(), "demo", True)
            elif layer in ("current_u", "current_v"):
                u, v = demo.demo_currents()
                self._set_layer("current_u", u, "demo", True)
                self._set_layer("current_v", v, "demo", True)

    def load_glider_index(self):
        self.glider_index = glider.ftp_index()

    def load_argo(self):
        self.argo_index = argo.fetch_region()


store = OceanStore()


# ---------- async refresh wrappers ----------
async def refresh_all():
    await asyncio.to_thread(store.load_layers)
    await asyncio.to_thread(store.load_glider_index)
    store.version += 1
    await _notify()


async def refresh_argo():
    await asyncio.to_thread(store.load_argo)
    store.version += 1
    await _notify()


# ---------- websocket fan-out ----------
_subscribers: set = set()

async def _notify():
    dead = []
    for ws in _subscribers:
        try:
            await ws.send_json({"type": "refresh", "version": store.version,
                                "layers": list(store.fields.keys())})
        except Exception:
            dead.append(ws)
    for ws in dead:
        _subscribers.discard(ws)