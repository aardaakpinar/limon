"""Platform adaptör arayüzleri. systemd/journald dışındaki platformlar (OpenRC, launchd,
Windows servisleri...) bu arayüzleri uygulayarak eklenebilir."""

from typing import Dict, List, Optional


class UnsupportedPlatformError(RuntimeError):
    """Platform / servis yöneticisi desteklenmiyor."""


class ServiceManager:
    name = "base"

    def list_failed(self) -> List[str]:
        raise NotImplementedError

    def show(self, unit: str) -> Dict[str, str]:
        """ActiveState, SubState, Result, NRestarts... gibi özellikler."""
        raise NotImplementedError

    def is_healthy(self, unit: str) -> bool:
        raise NotImplementedError

    def restart(self, unit: str) -> "tuple":
        """(ok, mesaj)"""
        raise NotImplementedError

    def reset_failed(self, unit: str) -> "tuple":
        raise NotImplementedError


class LogSource:
    name = "base"

    def tail(self, unit: str, lines: int, since_seconds: Optional[int] = None) -> List[dict]:
        """[{ts, priority, ident, message}] eskiden yeniye."""
        raise NotImplementedError

    def error_counts(self, since_seconds: int) -> Dict[str, dict]:
        """{birim: {"count": n, "sample": "son hata mesajı"}} (öncelik <= err)."""
        raise NotImplementedError


class HealthProbe:
    def disk_usage(self, mounts: List[str]) -> List[dict]:
        """[{mount, percent, free_bytes}]"""
        raise NotImplementedError
