"""Yerel politika motoru: AI ne önerirse önersin son söz burada.

Karar: DENY (reddet) | APPROVAL (kullanıcı onayı şart) | AUTO (onaysız yürüt).
danger.py korunur ve ek sinyal olarak kullanılır, tek sınır değildir: asıl sınırlar
tipli eylem listesi, olayla ilgili hedef kontrolü, korumalı birimler, yol kökleri ve hız sınırlarıdır."""

import fnmatch
import os
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .. import danger
from .actions import Action
from .config import DaemonConfig
from .store import Store

DENY, APPROVAL, AUTO = "deny", "approval", "auto"

_BASE_RISK = {"report_only": 0, "reset_failed": 1, "restart_service": 3, "edit_file": 7}

# edit_file asla dokunulmayacak desenler (izinli kök içinde bile)
_NEVER_EDIT = ("/.ssh/", "/.gnupg/", "/.aws/", "/.config/limon/", "/shadow", "/sudoers", "/etc/passwd")


@dataclass
class Decision:
    verdict: str
    risk: int
    reasons: List[str] = field(default_factory=list)

    def describe(self) -> str:
        return "; ".join(self.reasons) if self.reasons else "—"


def _match(name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def normalize_path(path: str) -> str:
    """Simge bağlantılarını ve '..' bileşenlerini çözerek kanonik yol."""
    return os.path.realpath(os.path.abspath(path))


def path_in_roots(path: str, roots: List[str]) -> bool:
    real = normalize_path(path)
    for r in roots:
        root = normalize_path(r)
        if real == root or real.startswith(root.rstrip(os.sep) + os.sep):
            return True
    return False


class Policy:
    def __init__(self, cfg: DaemonConfig, store: Store, clock: Callable[[], float] = time.time):
        self.cfg, self.store, self.clock = cfg, store, clock

    def evaluate(self, action: Action, event: dict, allowed_targets: Optional[List[str]] = None) -> Decision:
        cfg = self.cfg
        risk = _BASE_RISK.get(action.type, 10)
        reasons: List[str] = []

        if action.type == "report_only":
            return Decision(AUTO, 0, ["yalnızca rapor"])
        if cfg.mode == "off":
            return Decision(DENY, risk, ["daemon modu 'off': eylem yürütülmez"])

        if action.type in ("reset_failed", "restart_service"):
            unit = action.unit
            targets = allowed_targets if allowed_targets is not None else ([event["unit"]] if event.get("unit") else [])
            if unit not in targets:
                return Decision(DENY, risk, [f"{unit} bu olayla ilgili bir birim değil (hedefler: {targets or 'yok'})"])
            if _match(unit, ["limon-daemon*"]):
                return Decision(DENY, risk, ["daemon kendi servisini yeniden başlatamaz"])
            risk = max(risk, danger.assess_command(f"systemctl restart {unit}").score)
            protected = _match(unit, cfg.protected_units)
            if protected:
                risk = max(risk, 6)
                reasons.append(f"{unit} korumalı/kritik bir birim")
        elif action.type == "edit_file":
            protected = True  # dosya düzenleme hiçbir zaman otomatik değil
            if not cfg.allowed_roots:
                return Decision(DENY, risk, ["dosya düzenleme kapalı: 'allowed_roots' tanımlı değil"])
            real = normalize_path(action.path)
            if not path_in_roots(real, cfg.allowed_roots):
                return Decision(DENY, risk, [f"yol izinli köklerin dışında: {real}"])
            # Ayırıcıları '/' yap: aynı kural Windows ve POSIX'te çalışsın.
            real_slash = real.replace("\\", "/")
            if any(p in real_slash + "/" or real_slash.endswith(p) for p in _NEVER_EDIT):
                return Decision(DENY, risk, [f"hassas dosya düzenlenemez: {real}"])
            risk = max(risk, danger.assess_file_write(real, is_overwrite=True).score)
            reasons.append("dosya içeriği değişecek (yedek alınacak, doğrulama başarısızsa geri alınır)")
        else:
            return Decision(DENY, risk, [f"bilinmeyen eylem: {action.type}"])

        # döngü / hız sınırları
        now = self.clock()
        if event.get("fix_attempts", 0) >= cfg.max_fix_attempts_per_event:
            return Decision(DENY, risk, [f"olay için en fazla {cfg.max_fix_attempts_per_event} düzeltme denendi (döngü koruması)"])
        key = action.unit or action.path
        if cfg.max_actions_per_unit_per_hour and self.store.count_actions(now - 3600, key) >= cfg.max_actions_per_unit_per_hour:
            return Decision(DENY, risk, [f"{key} için saatlik eylem sınırı ({cfg.max_actions_per_unit_per_hour}) doldu"])
        if self.store.count_actions(now - 86400) >= cfg.max_actions_per_day:
            return Decision(DENY, risk, [f"günlük genel eylem sınırı ({cfg.max_actions_per_day}) doldu"])

        auto_ok = (
            cfg.mode == "auto"
            and not protected
            and action.type in cfg.auto_actions
            and action.type in ("reset_failed", "restart_service")
            and risk <= cfg.auto_max_risk
            and bool(cfg.auto_units) and _match(action.unit, cfg.auto_units)
        )
        if auto_ok:
            return Decision(AUTO, risk, reasons + ["otomatik modda izinli düşük riskli eylem"])
        if cfg.mode == "report":
            reasons.append("rapor modu: kullanıcı onayı gerekli")
        elif risk > cfg.auto_max_risk or protected:
            reasons.append("risk/korumalı birim nedeniyle kullanıcı onayı gerekli")
        else:
            reasons.append("bu eylem/birim otomatik izin listesinde değil: kullanıcı onayı gerekli")
        return Decision(APPROVAL, risk, reasons)
