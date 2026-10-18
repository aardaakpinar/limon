"""Doğrulanmış eylemlerin güvenli yürütülmesi. Kabuk yok: servis eylemleri adaptör
üzerinden argv ile, dosya düzenleme normalleştirilmiş yol + yedek + atomik yazma ile."""

import datetime
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional

from .actions import Action, ActionError
from .config import DaemonConfig
from .paths import Paths, ensure_private_dir
from .policy import normalize_path, path_in_roots

MAX_FILE_BYTES = 1_000_000


@dataclass
class ActionResult:
    ok: bool
    message: str
    rollback: Optional[dict] = None


class Executor:
    def __init__(self, cfg: DaemonConfig, paths: Paths, services):
        self.cfg, self.paths, self.services = cfg, paths, services

    def execute(self, action: Action) -> ActionResult:
        try:
            if action.type == "report_only":
                return ActionResult(True, "eylem yok")
            if action.type == "restart_service":
                ok, msg = self.services.restart(action.unit)
                return ActionResult(ok, f"restart {action.unit}: {msg}")
            if action.type == "reset_failed":
                ok, msg = self.services.reset_failed(action.unit)
                return ActionResult(ok, f"reset-failed {action.unit}: {msg}")
            if action.type == "edit_file":
                return self._edit_file(action)
        except Exception as e:  # yürütücü hiçbir zaman daemon'ı düşürmez
            return ActionResult(False, f"istisna: {e}")
        return ActionResult(False, f"desteklenmeyen eylem: {action.type}")

    # ---- dosya düzenleme ----------------------------------------------------------
    def _backup(self, real: str) -> str:
        ensure_private_dir(self.paths.backups)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        tag = hashlib.sha256(real.encode()).hexdigest()[:8]
        dest = os.path.join(self.paths.backups, f"{os.path.basename(real)}.{tag}.{ts}.bak")
        shutil.copy2(real, dest)
        os.chmod(dest, 0o600)
        return dest

    def _edit_file(self, a: Action) -> ActionResult:
        # Yol yürütme anında yeniden doğrulanır (politika kararından sonra simge bağlantısı değişmiş olabilir)
        if not self.cfg.allowed_roots:
            return ActionResult(False, "dosya düzenleme kapalı (allowed_roots yok)")
        real = normalize_path(a.path)
        if not path_in_roots(real, self.cfg.allowed_roots):
            return ActionResult(False, f"yol izinli köklerin dışında: {real}")
        if not os.path.isfile(real):
            return ActionResult(False, f"dosya bulunamadı: {real}")
        if os.path.getsize(real) > MAX_FILE_BYTES:
            return ActionResult(False, "dosya çok büyük")
        with open(real, "r", encoding="utf-8") as f:
            content = f.read()
        n = content.count(a.old_string)
        if n != 1:
            return ActionResult(False, f"old_string dosyada {n} kez geçiyor (tam 1 olmalı)")
        updated = content.replace(a.old_string, a.new_string, 1)
        backup = self._backup(real)
        st = os.stat(real)
        # atomik yazma: aynı dizinde geçici dosya + os.replace; izinler korunur
        fd, tmp = tempfile.mkstemp(prefix=".limon-", dir=os.path.dirname(real))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(updated)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, st.st_mode & 0o7777)
            if hasattr(os, "chown") and os.geteuid() == 0:
                os.chown(tmp, st.st_uid, st.st_gid)
            os.replace(tmp, real)
        except Exception as e:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return ActionResult(False, f"yazılamadı, dosya değişmedi: {e}")
        return ActionResult(True, f"{real} düzenlendi; yedek: {backup}", rollback={"path": real, "backup": backup})

    def rollback(self, info: dict) -> ActionResult:
        """Yedekten geri yükler (atomik)."""
        try:
            real, backup = info["path"], info["backup"]
            if not path_in_roots(real, self.cfg.allowed_roots):
                return ActionResult(False, "geri alma reddedildi: yol izinli köklerin dışında")
            if os.path.dirname(os.path.abspath(backup)) != os.path.abspath(self.paths.backups):
                return ActionResult(False, "geri alma reddedildi: yedek beklenen dizinde değil")
            st = os.stat(real)
            fd, tmp = tempfile.mkstemp(prefix=".limon-", dir=os.path.dirname(real))
            os.close(fd)
            shutil.copyfile(backup, tmp)
            os.chmod(tmp, st.st_mode & 0o7777)
            os.replace(tmp, real)
            return ActionResult(True, f"{real} yedekten geri yüklendi")
        except Exception as e:
            return ActionResult(False, f"geri alma başarısız: {e}")
