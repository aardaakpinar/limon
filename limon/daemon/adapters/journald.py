"""journald adaptörü (journalctl -o json)."""

import json
import re
from typing import Callable, Dict, List, Optional

from ..proc import ProcResult, run as default_run
from .base import LogSource

_UNIT_NAME = re.compile(r"^[A-Za-z0-9:_.@\-]+\.[a-z]+$")


def _msg(entry: dict) -> str:
    m = entry.get("MESSAGE", "")
    if isinstance(m, list):  # ikili mesaj: bayt dizisi
        try:
            return bytes(m).decode("utf-8", errors="replace")
        except (TypeError, ValueError):
            return ""
    return m if isinstance(m, str) else str(m)


def parse_entries(raw: str) -> List[dict]:
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(e, dict):
            continue
        try:
            ts = int(e.get("__REALTIME_TIMESTAMP", 0)) // 1_000_000
        except (TypeError, ValueError):
            ts = 0
        try:
            prio = int(e.get("PRIORITY", 6))
        except (TypeError, ValueError):
            prio = 6
        out.append({
            "ts": ts, "priority": prio,
            "ident": str(e.get("SYSLOG_IDENTIFIER", "")),
            "unit": str(e.get("_SYSTEMD_USER_UNIT") or e.get("_SYSTEMD_UNIT") or e.get("UNIT") or ""),
            "message": _msg(e),
        })
    return out


class JournaldSource(LogSource):
    name = "journald"

    def __init__(self, scope: str = "user", runner: Callable[..., ProcResult] = default_run,
                 timeout: int = 20, max_output: int = 2_000_000):
        self.scope = scope
        self._run = runner
        self.timeout = timeout
        self.max_output = max_output

    def _base(self) -> List[str]:
        return ["journalctl"] + (["--user"] if self.scope == "user" else []) + ["--no-pager", "-o", "json"]

    def tail(self, unit: str, lines: int, since_seconds: Optional[int] = None) -> List[dict]:
        if not _UNIT_NAME.match(unit):
            raise ValueError(f"geçersiz birim adı: {unit!r}")
        argv = self._base() + ["-u", unit, "-n", str(max(1, min(lines, 500)))]
        if since_seconds:
            argv += ["--since", f"-{int(since_seconds)}s"]
        res = self._run(argv, timeout=self.timeout, max_output=self.max_output)
        if not res.ok:
            raise RuntimeError(f"journalctl başarısız: {res.err.strip()[:200]}")
        return parse_entries(res.out)

    def error_counts(self, since_seconds: int) -> Dict[str, dict]:
        argv = self._base() + ["-p", "err", "--since", f"-{int(since_seconds)}s", "-n", "2000"]
        res = self._run(argv, timeout=self.timeout, max_output=self.max_output)
        if not res.ok:
            raise RuntimeError(f"journalctl başarısız: {res.err.strip()[:200]}")
        counts: Dict[str, dict] = {}
        for e in parse_entries(res.out):
            unit = e["unit"]
            if not unit or not _UNIT_NAME.match(unit):
                continue
            c = counts.setdefault(unit, {"count": 0, "sample": ""})
            c["count"] += 1
            c["sample"] = e["message"][:300]
        return counts
