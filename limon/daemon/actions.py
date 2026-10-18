"""Tipli eylemler. AI yalnızca bu şemaya uyan, doğrulanabilir eylemler önerebilir;
serbest metin komut yoktur."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Optional

UNIT_RE = re.compile(r"^[A-Za-z0-9:_.@\-]{1,200}\.(service|timer|socket|path|mount)$")
MAX_EDIT_CHARS = 20_000

ACTION_TYPES = ("report_only", "reset_failed", "restart_service", "edit_file")


class ActionError(ValueError):
    pass


@dataclass(frozen=True)
class Action:
    type: str
    unit: str = ""
    path: str = ""
    old_string: str = ""
    new_string: str = ""
    reason: str = ""

    def canonical(self) -> dict:
        d = {"type": self.type}
        if self.type in ("reset_failed", "restart_service"):
            d["unit"] = self.unit
        elif self.type == "edit_file":
            d.update(path=self.path, old_string=self.old_string, new_string=self.new_string)
        return d

    def digest(self) -> str:
        """Onayın bağlandığı parmak izi: eylem değişirse onay geçersiz olur."""
        blob = json.dumps(self.canonical(), sort_keys=True, ensure_ascii=False).encode()
        return hashlib.sha256(blob).hexdigest()

    def describe(self) -> str:
        if self.type == "report_only":
            return "yalnızca rapor (eylem yok)"
        if self.type in ("reset_failed", "restart_service"):
            return f"{self.type} {self.unit}"
        if self.type == "edit_file":
            return f"edit_file {self.path} ({len(self.old_string)}→{len(self.new_string)} karakter)"
        return self.type

    def to_dict(self) -> dict:
        d = self.canonical()
        d["reason"] = self.reason
        return d


def _s(raw: dict, key: str, limit: int = 1000) -> str:
    v = raw.get(key, "")
    if v is None:
        return ""
    if not isinstance(v, str):
        raise ActionError(f"'{key}' metin olmalı")
    if len(v) > limit:
        raise ActionError(f"'{key}' çok uzun")
    return v


def parse_action(raw) -> Action:
    """Ham (AI'dan gelen) sözlüğü doğrular; geçersizse ActionError."""
    if not isinstance(raw, dict):
        raise ActionError("eylem bir nesne olmalı")
    atype = raw.get("type")
    if atype not in ACTION_TYPES:
        raise ActionError(f"izin verilmeyen eylem türü: {str(atype)[:40]!r}")
    reason = _s(raw, "reason", 500)
    if atype == "report_only":
        return Action(type=atype, reason=reason)
    if atype in ("reset_failed", "restart_service"):
        unit = _s(raw, "unit", 200)
        if not UNIT_RE.match(unit):
            raise ActionError(f"geçersiz servis adı: {unit[:60]!r}")
        return Action(type=atype, unit=unit, reason=reason)
    # edit_file
    path = _s(raw, "path", 4096)
    old, new = _s(raw, "old_string", MAX_EDIT_CHARS), _s(raw, "new_string", MAX_EDIT_CHARS)
    if not path or "\x00" in path or not path.startswith("/"):
        raise ActionError("edit_file için mutlak bir yol gerekli")
    if not old:
        raise ActionError("old_string boş olamaz")
    if old == new:
        raise ActionError("old_string ile new_string aynı")
    return Action(type=atype, path=path, old_string=old, new_string=new, reason=reason)
