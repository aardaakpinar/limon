"""Platform seçimi. Yalnızca Linux + systemd desteklenir; diğerleri açık hata verir."""

import os
import shutil
import sys
from dataclasses import dataclass

from .base import HealthProbe, LogSource, ServiceManager, UnsupportedPlatformError
from .journald import JournaldSource
from .system import SystemProbe
from .systemd import SystemdManager


@dataclass
class Platform:
    services: ServiceManager
    logs: LogSource
    probe: HealthProbe


def systemd_available() -> bool:
    # sd_booted(): bu dizin yalnızca systemd ile açılmış sistemlerde vardır
    return os.path.isdir("/run/systemd/system") and shutil.which("systemctl") is not None


def check_supported() -> None:
    if not sys.platform.startswith("linux"):
        raise UnsupportedPlatformError(
            f"limon daemon şimdilik yalnızca Linux + systemd üzerinde çalışır (bu sistem: {sys.platform}). "
            "macOS (launchd), Windows ve OpenRC için adaptör henüz yok."
        )
    if not systemd_available():
        raise UnsupportedPlatformError(
            "Bu sistemde systemd bulunamadı (/run/systemd/system yok veya 'systemctl' kurulu değil). "
            "limon daemon systemd gerektirir; OpenRC/runit desteği henüz eklenmedi."
        )
    if not shutil.which("journalctl"):
        raise UnsupportedPlatformError("'journalctl' bulunamadı; journald olmadan log izlenemez.")


def detect_platform(cfg) -> Platform:
    check_supported()
    kw = dict(timeout=cfg.command_timeout)
    return Platform(
        services=SystemdManager(cfg.scope, max_output=cfg.command_max_output, **kw),
        logs=JournaldSource(cfg.scope, **kw),
        probe=SystemProbe(),
    )
