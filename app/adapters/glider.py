"""
Glider data — ftp://ftp.ifremer.fr/ifremer/glider/v2
Primary: FTP directory index (matches your link exactly).
Optional: IFREMER ERDDAP (OceanGliders GDAC) for actual track points.
"""
import ftplib
import httpx
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import GLIDER_FTP_HOST, GLIDER_FTP_PATH, GLIDER_ERDDAP


def ftp_index(limit: int = 100) -> dict:
    """List glider mission directories available on the IFREMER GDAC FTP."""
    missions = []
    try:
        ftp = ftplib.FTP(GLIDER_FTP_HOST, timeout=30)
        ftp.login("anonymous", "guest")
        ftp.cwd(GLIDER_FTP_PATH)

        def _add(name):
            if name.startswith("."):
                return
            missions.append({"mission": name, "path": f"{GLIDER_FTP_PATH}/{name}"})

        entries = ftp.nlst()
        for name in entries[:limit]:
            try:
                ftp.cwd(name)
                _add(name)
                ftp.cwd("..")
            except ftplib.error_perm:
                continue
        ftp.quit()
        return {"missions": missions, "source": f"ftp://{GLIDER_FTP_HOST}{GLIDER_FTP_PATH}"}
    except Exception as e:
        print(f"[glider] FTP failed: {e}")
        return {"missions": [], "source": "ftp", "error": str(e)}


def erddap_tracks(lat_min=-40, lat_max=30, lon_min=30, lon_max=110, limit=500) -> dict:
    """Real glider GPS track points from IFREMER ERDDAP (CSV)."""
    url = f"{GLIDER_ERDDAP}.csv"
    query = (f"?platform_id,latitude,longitude,time"
             f"&latitude>={lat_min}&latitude<={lat_max}"
             f"&longitude>={lon_min}&longitude<={lon_max}")
    try:
        r = httpx.get(url, params=query, timeout=60, follow_redirects=True)
        r.raise_for_status()
        lines = r.text.strip().splitlines()
        header = lines[0].split(",")
        rows = [l.split(",") for l in lines[1:limit + 1]]
        idx = {k: header.index(k) for k in ("platform_id", "latitude", "longitude", "time")}
        points = [{"platform": r[idx["platform_id"]].strip('"'),
                   "lat": float(r[idx["latitude"]]),
                   "lon": float(r[idx["longitude"]]),
                   "time": r[idx["time"]].strip('"')} for r in rows if len(r) >= len(header)]
        return {"points": points, "source": "IFREMER ERDDAP / OceanGliders GDAC"}
    except Exception as e:
        print(f"[glider] ERDDAP failed: {e}")
        return {"points": [], "error": str(e)}