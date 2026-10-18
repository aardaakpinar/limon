"""Daemon ayarları: ana config.json içindeki "daemon" bölümü. Eksik/bozuk değerler
güvenli varsayılana döner ve sınırlara kırpılır."""

from dataclasses import dataclass, field, fields
from typing import List

MODES = ("off", "report", "auto")

DEFAULT_PROTECTED = [
    "sshd*", "ssh.service", "ssh@*", "systemd-*", "dbus*", "polkit*", "NetworkManager*",
    "display-manager*", "gdm*", "sddm*", "lightdm*", "getty@*", "user@*", "user-runtime-dir@*",
    "login*", "firewalld*", "ufw*", "auditd*", "limon-daemon*",
]


@dataclass
class DaemonConfig:
    scope: str = "user"                 # user | system
    mode: str = "report"                # off: yalnızca olay izle | report: teşhis + onay kuyruğu | auto: izinli düşük riskli eylemler onaysız
    poll_interval: int = 30
    cooldown: int = 3600                # aynı olay için yeniden işleme bekleme süresi (sn)
    watch_units: List[str] = field(default_factory=list)    # boş = tüm başarısız servisler
    ignore_units: List[str] = field(default_factory=list)
    journal_lines: int = 60
    journal_max_chars: int = 6000
    context_max_chars: int = 12000
    error_burst_threshold: int = 5
    error_burst_window: int = 300
    flap_threshold: int = 3
    disk_mounts: List[str] = field(default_factory=lambda: ["/"])
    disk_warn: int = 85
    disk_crit: int = 95
    max_diagnosis_attempts: int = 5
    max_fix_attempts_per_event: int = 3
    max_actions_per_unit_per_hour: int = 3
    max_actions_per_day: int = 20
    approval_ttl: int = 86400
    auto_actions: List[str] = field(default_factory=lambda: ["reset_failed", "restart_service"])
    auto_max_risk: int = 3
    auto_units: List[str] = field(default_factory=list)     # boş = hiçbir servis için otomatik eylem yok
    protected_units: List[str] = field(default_factory=lambda: list(DEFAULT_PROTECTED))
    allowed_roots: List[str] = field(default_factory=list)  # edit_file için izinli kök dizinler (boş = kapalı)
    retention_days: int = 14
    max_events: int = 2000
    audit_max_bytes: int = 1_000_000
    audit_backups: int = 3
    verify_delay: int = 5
    ipc_group: str = ""                 # boş: yalnızca daemon'ı çalıştıran kullanıcı
    command_timeout: int = 20
    command_max_output: int = 200_000
    danger_threshold: int = 5
    # İnternet araması (varsayılan KAPALI; sorgular üçüncü tarafa gider)
    web_search: str = "off"             # off | searxng | brave
    web_search_url: str = ""            # searxng örnek adresi (ör. http://localhost:8080)
    web_search_max_rounds: int = 2      # teşhis başına en fazla arama turu
    web_search_daily_limit: int = 30
    web_search_results: int = 5


_LIMITS = {
    "poll_interval": (5, 3600), "cooldown": (30, 7 * 86400), "journal_lines": (5, 500),
    "journal_max_chars": (500, 50_000), "context_max_chars": (1000, 100_000),
    "error_burst_threshold": (2, 10_000), "error_burst_window": (30, 86400), "flap_threshold": (2, 1000),
    "disk_warn": (50, 99), "disk_crit": (51, 100), "max_diagnosis_attempts": (1, 20),
    "max_fix_attempts_per_event": (0, 10), "max_actions_per_unit_per_hour": (0, 100),
    "max_actions_per_day": (0, 1000), "approval_ttl": (60, 30 * 86400), "auto_max_risk": (0, 5),
    "retention_days": (1, 365), "max_events": (50, 100_000), "audit_max_bytes": (10_000, 100_000_000),
    "audit_backups": (0, 20), "verify_delay": (0, 120), "command_timeout": (2, 300),
    "command_max_output": (1000, 5_000_000), "danger_threshold": (0, 10),
    "web_search_max_rounds": (0, 4), "web_search_daily_limit": (0, 1000), "web_search_results": (1, 8),
}


def from_cfg(cfg: dict) -> DaemonConfig:
    raw = cfg.get("daemon", {}) if isinstance(cfg, dict) else {}
    if not isinstance(raw, dict):
        raw = {}
    dc = DaemonConfig()
    for f in fields(DaemonConfig):
        if f.name not in raw:
            continue
        value = raw[f.name]
        default = getattr(dc, f.name)
        if isinstance(default, bool) or isinstance(default, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
            lo, hi = _LIMITS.get(f.name, (value, value))
            value = max(lo, min(hi, value))
        elif isinstance(default, list):
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                continue
        elif isinstance(default, str):
            if not isinstance(value, str):
                continue
        setattr(dc, f.name, value)
    if dc.mode not in MODES:
        dc.mode = "report"
    if dc.scope not in ("user", "system"):
        dc.scope = "user"
    if dc.web_search not in ("off", "searxng", "brave"):
        dc.web_search = "off"
    if dc.disk_crit <= dc.disk_warn:
        dc.disk_crit = min(100, dc.disk_warn + 5)
    # korumalı liste yalnızca genişletilebilir: kullanıcı eklemeleri varsayılanlara eklenir
    for pat in DEFAULT_PROTECTED:
        if pat not in dc.protected_units:
            dc.protected_units.append(pat)
    return dc
