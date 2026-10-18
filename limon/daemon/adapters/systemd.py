"""systemd adaptörü (systemctl). Kabuk yok; yalnızca argv."""

import re
from typing import Callable, Dict, List

from ..proc import ProcResult, run as default_run
from .base import ServiceManager

_SHOW_PROPS = "ActiveState,SubState,LoadState,Result,NRestarts,ExecMainStatus,MainPID,Description"
_UNIT_NAME = re.compile(r"^[A-Za-z0-9:_.@\-]+\.[a-z]+$")


class SystemdManager(ServiceManager):
    name = "systemd"

    def __init__(self, scope: str = "user", runner: Callable[..., ProcResult] = default_run,
                 timeout: int = 20, max_output: int = 200_000):
        self.scope = scope
        self._run = runner
        self.timeout = timeout
        self.max_output = max_output

    def _ctl(self, *args: str) -> ProcResult:
        argv = ["systemctl"] + (["--user"] if self.scope == "user" else []) + list(args)
        return self._run(argv, timeout=self.timeout, max_output=self.max_output)

    def list_failed(self) -> List[str]:
        res = self._ctl("list-units", "--state=failed", "--type=service", "--no-legend", "--plain", "--no-pager")
        if not res.ok:
            raise RuntimeError(f"systemctl list-units başarısız: {res.err.strip()[:200]}")
        units = []
        for line in res.out.splitlines():
            parts = line.replace("●", " ").replace("*", " ").split()
            if parts and _UNIT_NAME.match(parts[0]):
                units.append(parts[0])
        return units

    def show(self, unit: str) -> Dict[str, str]:
        if not _UNIT_NAME.match(unit):
            raise ValueError(f"geçersiz birim adı: {unit!r}")
        res = self._ctl("show", unit, f"--property={_SHOW_PROPS}", "--no-pager")
        props: Dict[str, str] = {}
        for line in res.out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k] = v
        return props

    def is_healthy(self, unit: str) -> bool:
        p = self.show(unit)
        return p.get("ActiveState") == "active" and p.get("SubState") not in ("auto-restart",)

    def restart(self, unit: str):
        if not _UNIT_NAME.match(unit):
            return False, f"geçersiz birim adı: {unit!r}"
        res = self._ctl("restart", unit)
        return res.ok, (res.err.strip() or res.out.strip() or "tamam")[:300]

    def reset_failed(self, unit: str):
        if not _UNIT_NAME.match(unit):
            return False, f"geçersiz birim adı: {unit!r}"
        res = self._ctl("reset-failed", unit)
        return res.ok, (res.err.strip() or res.out.strip() or "tamam")[:300]
