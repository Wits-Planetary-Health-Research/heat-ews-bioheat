"""Pull hourly ERA5 2 m temperature for a small block around Soweto and RMMCH from the public
NSF NCAR ERA5 copy on AWS (s3://nsf-ncar-era5, no account needed), using ranged reads.

Output: data/era5_ncar/2t_YYYYMM.npz with hourly UTC times, lats, lons and values in degrees C.
Usage: python scripts/pull_ncar_era5.py 1991 2026
"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import calendar
import sys

import fsspec
import h5py
import numpy as np
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "era5_ncar"
BASE = "https://nsf-ncar-era5.s3.amazonaws.com"
LAT = (-25.75, -26.75)   # north to south, matches file order
LON = (27.5, 28.25)


def url(y, m):
    last = calendar.monthrange(y, m)[1]
    return f"{BASE}/e5.oper.an.sfc/{y}{m:02d}/e5.oper.an.sfc.128_167_2t.ll025sc.{y}{m:02d}0100_{y}{m:02d}{last}23.nc"


def pull(ym):
    y, m = ym
    f = OUT / f"2t_{y}{m:02d}.npz"
    if f.exists():
        return ym, "cached"
    u = url(y, m)
    if requests.head(u, timeout=60).status_code != 200:
        return ym, "missing"
    for attempt in range(3):
        try:
            with fsspec.open(u, block_size=2**22, cache_type="none").open() as fh, h5py.File(fh, "r") as h:
                lat, lon = h["latitude"][:], h["longitude"][:]
                i0, i1 = int(np.argmin(abs(lat - LAT[0]))), int(np.argmin(abs(lat - LAT[1])))
                j0, j1 = int(np.argmin(abs(lon - LON[0]))), int(np.argmin(abs(lon - LON[1])))
                v = h["VAR_2T"][:, i0:i1 + 1, j0:j1 + 1] - 273.15
                t = h["time"][:]
                tunits = h["time"].attrs.get("units", b"").decode() if isinstance(h["time"].attrs.get("units"), bytes) else str(h["time"].attrs.get("units"))
            np.savez_compressed(f, v=v.astype("float32"), t=t, tunits=tunits, lat=lat[i0:i1 + 1], lon=lon[j0:j1 + 1], src=u)
            return ym, "ok"
        except Exception as e:  # network hiccup, retry
            err = e
    return ym, f"failed: {err}"


if __name__ == "__main__":
    y0, y1 = int(sys.argv[1]), int(sys.argv[2])
    OUT.mkdir(parents=True, exist_ok=True)
    months = [(y, m) for y in range(y0, y1 + 1) for m in range(1, 13)]
    with ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 8) as ex:
        for ym, status in ex.map(pull, months):
            print(f"{ym[0]}-{ym[1]:02d} {status}", flush=True)
