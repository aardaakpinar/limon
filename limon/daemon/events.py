"""Sistem olaylarını toplar ve normalleştirir. Tekilleştirme/cooldown store.record_event
içindedir; burada yalnızca parmak izi üretimi ve olay tespiti vardır."""

import fnmatch
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List

from .config import DaemonConfig
from .store import Store

KIND_UNIT_FAILED = "unit_failed"
KIND_UNIT_FLAPPING = "unit_flapping"
KIND_ERROR_BURST = "error_burst"
KIND_DISK = "disk_usage"
KIND_MANUAL = "manual_diagnose"

# resolve_missing yalnızca koşulu yeniden değerlendirebildiğimiz türler için kullanılır
AUTO_RESOLVED_KINDS = (KIND_UNIT_FAILED, KIND_UNIT_FLAPPING, KIND_ERROR_BURST, KIND_DISK)


@dataclass
class Event:
    kind: str
    unit: str
    severity: str
    summary: str
    fingerprint: str
    detail: Dict = field(default_factory=dict)


def make_fingerprint(kind: str, unit: str = "", key: str = "") -> str:
    return hashlib.sha256(f"{kind}|{unit}|{key}".encode()).hexdigest()[:24]


def _match(name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


class EventCollector:
    """Bir tarama turunda tüm kaynaklardan Event listesi üretir."""

    def __init__(self, cfg: DaemonConfig, platform, store: Store, clock: Callable[[], float] = time.time):
        self.cfg, self.p, self.store, self.clock = cfg, platform, store, clock

    def _wanted(self, unit: str) -> bool:
        if _match(unit, self.cfg.ignore_units):
            return False
        return not self.cfg.watch_units or _match(unit, self.cfg.watch_units)

    def collect(self) -> List[Event]:
        events: List[Event] = []
        events += self._failed_units()
        events += self._error_bursts()
        events += self._disk()
        return events

    def _failed_units(self) -> List[Event]:
        out = []
        for unit in self.p.services.list_failed():
            if not self._wanted(unit):
                continue
            props = self.p.services.show(unit)
            out.append(Event(
                KIND_UNIT_FAILED, unit, "critical", f"{unit} başarısız durumda (Result={props.get('Result', '?')})",
                make_fingerprint(KIND_UNIT_FAILED, unit), {"props": props},
            ))
        # yeniden başlama döngüsü: NRestarts taban değerinden flap_threshold kadar arttıysa
        for unit in list(self._candidate_units()):
            if not self._wanted(unit):
                continue
            props = self.p.services.show(unit)
            try:
                n = int(props.get("NRestarts", "0") or 0)
            except ValueError:
                continue
            key = f"nrestarts:{unit}"
            base = self.store.kv_get(key)
            if base is None:
                self.store.kv_set(key, str(n))
                continue
            if n < int(base):  # sayaç sıfırlandı
                self.store.kv_set(key, str(n))
            elif n - int(base) >= self.cfg.flap_threshold:
                out.append(Event(
                    KIND_UNIT_FLAPPING, unit, "warning", f"{unit} sürekli yeniden başlıyor (+{n - int(base)} yeniden başlatma)",
                    make_fingerprint(KIND_UNIT_FLAPPING, unit), {"props": props},
                ))
                self.store.kv_set(key, str(n))
        return out

    def _candidate_units(self):
        # yalnızca açıkça izlenen birimlerde NRestarts takibi (tüm servisleri her turda sorgulamayalım)
        return [u for u in self.cfg.watch_units if "*" not in u and "?" not in u]

    def _error_bursts(self) -> List[Event]:
        out = []
        for unit, info in self.p.logs.error_counts(self.cfg.error_burst_window).items():
            if info["count"] < self.cfg.error_burst_threshold or not self._wanted(unit):
                continue
            out.append(Event(
                KIND_ERROR_BURST, unit, "warning",
                f"{unit}: son {self.cfg.error_burst_window // 60 or 1} dk içinde {info['count']} hata kaydı",
                make_fingerprint(KIND_ERROR_BURST, unit), {"count": info["count"], "sample": info["sample"]},
            ))
        return out

    def _disk(self) -> List[Event]:
        out = []
        for d in self.p.probe.disk_usage(self.cfg.disk_mounts):
            if d["percent"] >= self.cfg.disk_crit:
                level, sev = "crit", "critical"
            elif d["percent"] >= self.cfg.disk_warn:
                level, sev = "warn", "warning"
            else:
                continue
            out.append(Event(
                KIND_DISK, "", sev, f"Disk %{d['percent']} dolu: {d['mount']}",
                make_fingerprint(KIND_DISK, "", f"{d['mount']}:{level}"), {"disk": d},
            ))
        return out
