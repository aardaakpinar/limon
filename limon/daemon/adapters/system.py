"""Temel sistem sağlığı: disk kullanımı."""

import shutil
from typing import List

from .base import HealthProbe


class SystemProbe(HealthProbe):
    def disk_usage(self, mounts: List[str]) -> List[dict]:
        out = []
        for m in mounts:
            try:
                u = shutil.disk_usage(m)
            except OSError:
                continue
            if u.total <= 0:
                continue
            out.append({"mount": m, "percent": int(u.used * 100 / u.total), "free_bytes": u.free})
        return out
