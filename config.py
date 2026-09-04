import os
import json
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = ["*"] if _raw_origins.strip() == "*" else [o.strip() for o in _raw_origins.split(",") if o.strip()]

CMEMS_USERNAME = os.getenv("CMEMS_USERNAME", "")
CMEMS_PASSWORD = os.getenv("CMEMS_PASSWORD", "")
CMEMS_DATASET_ID = os.getenv("CMEMS_DATASET_ID", "cmems_mod_glo_phy_my_0.083deg_P1D-m")

INCOIS_OPENDAP_URLS: dict = json.loads(os.getenv("INCOIS_OPENDAP_URLS", "{}"))

ARGO_BACKEND = os.getenv("ARGO_BACKEND", "erddap")
try:
    ARGO_BBOX = json.loads(os.getenv("ARGO_BBOX", "[50,110,-35,30]"))
except Exception:
    ARGO_BBOX = [50, 110, -35, 30]

GLIDER_FTP_HOST = "ftp.ifremer.fr"
GLIDER_FTP_PATH = "/ifremer/glider/v2"
GLIDER_ERDDAP = "https://erddap.ifremer.fr/erddap/tabledap/OceanGlidersGDACTrajectoryArchive"

DEFAULT_STRIDE = int(os.getenv("DEFAULT_STRIDE", "2"))
REFRESH_HOURS = float(os.getenv("REFRESH_HOURS", "6"))

# Default analysis window (Indian Ocean) — change to global if you have bandwidth
DEFAULT_BBOX = dict(min_lon=30, max_lon=110, min_lat=-40, max_lat=30, min_depth=0, max_depth=2000)

# Which layer each Copernicus variable maps to
LAYERS = {
    "temperature": {"cmems_var": "thetao", "units": "°C",   "label": "Sea Water Temperature"},
    "salinity":    {"cmems_var": "so",     "units": "PSU",  "label": "Sea Water Salinity"},
    "current_u":   {"cmems_var": "uo",     "units": "m/s",  "label": "Eastward Current"},
    "current_v":   {"cmems_var": "vo",     "units": "m/s",  "label": "Northward Current"},
    "ssh":         {"cmems_var": "zos",    "units": "m",    "label": "Sea Surface Height"},
}