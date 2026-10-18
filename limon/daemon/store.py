"""Kalıcı durum: olaylar, onay görevleri, eylem günlüğü, anahtar-değer. SQLite (stdlib),
tek bağlantı + kilit; daemon yeniden başladığında kaldığı yerden devam eder.
Audit günlüğü ayrı bir boyut-sınırlı JSONL dosyasıdır."""

import json
import os
import secrets
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from .redact import safe

SCHEMA_VERSION = 1

OPEN_STATUSES = ("new", "pending_diagnosis", "diagnosing", "awaiting_approval")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fingerprint TEXT NOT NULL, kind TEXT NOT NULL, unit TEXT NOT NULL DEFAULT '',
  severity TEXT NOT NULL DEFAULT 'warning', summary TEXT NOT NULL DEFAULT '',
  detail TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'new',
  count INTEGER NOT NULL DEFAULT 1, first_seen REAL NOT NULL, last_seen REAL NOT NULL,
  last_processed REAL NOT NULL DEFAULT 0, diag_attempts INTEGER NOT NULL DEFAULT 0,
  fix_attempts INTEGER NOT NULL DEFAULT 0, next_retry REAL NOT NULL DEFAULT 0,
  diagnosis TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ev_fp ON events(fingerprint, id);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, event_id INTEGER NOT NULL, action TEXT NOT NULL, digest TEXT NOT NULL,
  risk INTEGER NOT NULL, reasons TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
  created REAL NOT NULL, decided REAL NOT NULL DEFAULT 0, expires REAL NOT NULL,
  result TEXT NOT NULL DEFAULT '', rollback TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS action_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, unit TEXT NOT NULL, type TEXT NOT NULL, ok INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""

_EVENT_FIELDS = {
    "severity", "summary", "detail", "status", "count", "last_seen", "last_processed",
    "diag_attempts", "fix_attempts", "next_retry", "diagnosis", "note",
}
_TASK_FIELDS = {"status", "decided", "result", "rollback"}


class Store:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(_SCHEMA)
            self._db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def close(self):
        with self._lock:
            self._db.close()

    # ---- olaylar -----------------------------------------------------------
    def record_event(self, ev, cooldown: int, now: Optional[float] = None):
        """Olayı kaydeder. (event_id, işlenmeli_mi) döndürür.
        Tekilleştirme: aynı parmak izi açıkken ya da cooldown içindeyken yalnızca sayaç artar."""
        now = time.time() if now is None else now
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM events WHERE fingerprint=? ORDER BY id DESC LIMIT 1", (ev.fingerprint,)
            ).fetchone()
            detail = json.dumps(ev.detail, ensure_ascii=False)
            if row is not None:
                self._db.execute("UPDATE events SET count=count+1, last_seen=? WHERE id=?", (now, row["id"]))
                if row["status"] in OPEN_STATUSES:
                    return row["id"], False
                if now - row["last_processed"] < cooldown:
                    if row["status"] == "resolved":
                        self._db.execute("UPDATE events SET status='suppressed' WHERE id=?", (row["id"],))
                    return row["id"], False
            cur = self._db.execute(
                "INSERT INTO events(fingerprint,kind,unit,severity,summary,detail,status,first_seen,last_seen) "
                "VALUES(?,?,?,?,?,?,'new',?,?)",
                (ev.fingerprint, ev.kind, ev.unit, ev.severity, safe(ev.summary, 500, False), detail, now, now),
            )
            return cur.lastrowid, True

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            r = self._db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return dict(r) if r else None

    def claim_event(self, event_id: int) -> bool:
        """Olayı atomik olarak 'diagnosing' durumuna alır (aynı olayı iki iş parçacığı işlemesin)."""
        with self._lock:
            n = self._db.execute(
                "UPDATE events SET status='diagnosing' WHERE id=? AND status IN ('new','pending_diagnosis')", (event_id,)
            ).rowcount
        return n == 1

    def update_event(self, event_id: int, **fields) -> None:
        bad = set(fields) - _EVENT_FIELDS
        if bad:
            raise ValueError(f"izin verilmeyen alan: {bad}")
        if not fields:
            return
        sets = ", ".join(f"{k}=?" for k in fields)
        with self._lock:
            self._db.execute(f"UPDATE events SET {sets} WHERE id=?", (*fields.values(), event_id))

    def list_events(self, limit: int = 20, since: Optional[float] = None) -> List[Dict[str, Any]]:
        q, args = "SELECT * FROM events", []
        if since:
            q += " WHERE last_seen>=?"
            args.append(since)
        q += " ORDER BY id DESC LIMIT ?"
        args.append(max(1, min(limit, 500)))
        with self._lock:
            return [dict(r) for r in self._db.execute(q, args).fetchall()]

    def due_for_diagnosis(self, now: float) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM events WHERE status IN ('new','pending_diagnosis') AND next_retry<=? ORDER BY id", (now,)
            ).fetchall()
        return [dict(r) for r in rows]

    def resolve_missing(self, kind_prefixes, active_fingerprints, now: float) -> int:
        """Koşulu ortadan kalkan açık olayları 'resolved' yapar."""
        n = 0
        with self._lock:
            rows = self._db.execute(
                "SELECT id, fingerprint, kind FROM events WHERE status NOT IN ('resolved','suppressed','gave_up','diagnosis_failed','fixed') "
                "AND id IN (SELECT MAX(id) FROM events GROUP BY fingerprint)"
            ).fetchall()
            for r in rows:
                if r["kind"] in kind_prefixes and r["fingerprint"] not in active_fingerprints:
                    self._db.execute("UPDATE events SET status='resolved', last_seen=? WHERE id=?", (now, r["id"]))
                    n += 1
        return n

    def recover_after_restart(self) -> Dict[str, int]:
        """Çökme/yeniden başlatma sonrası: yarım kalan işleri güvenli duruma al.
        - 'diagnosing' -> 'pending_diagnosis' (tekrar denenir, olay kaybolmaz)
        - 'executing' görevler -> 'failed' (sonucu bilinmiyor; kendiliğinden TEKRAR yürütülmez)"""
        with self._lock:
            a = self._db.execute("UPDATE events SET status='pending_diagnosis' WHERE status='diagnosing'").rowcount
            b = self._db.execute(
                "UPDATE tasks SET status='failed', result='daemon yürütme sırasında yeniden başladı; sonuç bilinmiyor' "
                "WHERE status='executing'"
            ).rowcount
        return {"events": a, "tasks": b}

    # ---- görevler (onay kuyruğu) ---------------------------------------------
    def add_task(self, event_id: int, action: dict, digest: str, risk: int, reasons: str,
                 status: str, ttl: int, now: Optional[float] = None) -> str:
        now = time.time() if now is None else now
        with self._lock:
            for _ in range(10):
                tid = secrets.token_hex(4)
                if not self._db.execute("SELECT 1 FROM tasks WHERE id=?", (tid,)).fetchone():
                    break
            self._db.execute(
                "INSERT INTO tasks(id,event_id,action,digest,risk,reasons,status,created,expires) VALUES(?,?,?,?,?,?,?,?,?)",
                (tid, event_id, json.dumps(action, ensure_ascii=False), digest, risk, reasons, status, now, now + ttl),
            )
        return tid

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            r = self._db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(r) if r else None

    def update_task(self, task_id: str, **fields) -> None:
        bad = set(fields) - _TASK_FIELDS
        if bad:
            raise ValueError(f"izin verilmeyen alan: {bad}")
        sets = ", ".join(f"{k}=?" for k in fields)
        with self._lock:
            self._db.execute(f"UPDATE tasks SET {sets} WHERE id=?", (*fields.values(), task_id))

    def transition_task(self, task_id: str, from_status: str, to_status: str, now: Optional[float] = None) -> bool:
        """Atomik durum geçişi (çifte onay / yarış durumlarını engeller)."""
        now = time.time() if now is None else now
        with self._lock:
            n = self._db.execute(
                "UPDATE tasks SET status=?, decided=? WHERE id=? AND status=?", (to_status, now, task_id, from_status)
            ).rowcount
        return n == 1

    def list_tasks(self, statuses=None, event_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        q, args, conds = "SELECT * FROM tasks", [], []
        if statuses:
            conds.append("status IN (%s)" % ",".join("?" * len(statuses)))
            args += list(statuses)
        if event_id is not None:
            conds.append("event_id=?")
            args.append(event_id)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY created DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            return [dict(r) for r in self._db.execute(q, args).fetchall()]

    def expire_tasks(self, now: float) -> int:
        with self._lock:
            return self._db.execute(
                "UPDATE tasks SET status='expired', decided=? WHERE status='pending' AND expires<?", (now, now)
            ).rowcount

    # ---- eylem günlüğü (hız sınırı) -------------------------------------------
    def record_action(self, unit: str, atype: str, ok: bool, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            self._db.execute("INSERT INTO action_log(ts,unit,type,ok) VALUES(?,?,?,?)", (now, unit, atype, int(ok)))

    def count_actions(self, since: float, unit: Optional[str] = None) -> int:
        q, args = "SELECT COUNT(*) FROM action_log WHERE ts>=?", [since]
        if unit is not None:
            q += " AND unit=?"
            args.append(unit)
        with self._lock:
            return self._db.execute(q, args).fetchone()[0]

    # ---- anahtar-değer ---------------------------------------------------------
    def kv_get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._lock:
            r = self._db.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        return r["v"] if r else default

    def kv_set(self, key: str, value: str) -> None:
        with self._lock:
            self._db.execute("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, value))

    # ---- saklama politikası ------------------------------------------------------
    def purge(self, retention_days: int, max_events: int, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        cutoff = now - retention_days * 86400
        with self._lock:
            n = self._db.execute(
                "DELETE FROM events WHERE last_seen<? AND status NOT IN ('new','pending_diagnosis','diagnosing','awaiting_approval')",
                (cutoff,),
            ).rowcount
            n += self._db.execute(
                "DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT ?) "
                "AND status NOT IN ('new','pending_diagnosis','diagnosing','awaiting_approval')", (max_events,)
            ).rowcount
            self._db.execute(
                "DELETE FROM tasks WHERE status NOT IN ('pending','approved','executing') AND created<?", (cutoff,)
            )
            self._db.execute("DELETE FROM action_log WHERE ts<?", (now - 2 * 86400,))
        return n


class AuditLog:
    """Boyut sınırlı, döndürülen JSONL işlem günlüğü (0600). Girdiler redakte edilir."""

    def __init__(self, path: str, max_bytes: int = 1_000_000, backups: int = 3):
        self.path, self.max_bytes, self.backups = path, max_bytes, backups
        self._lock = threading.Lock()

    def _rotate(self):
        if self.backups <= 0:
            os.replace(self.path, self.path + ".tmp")
            os.remove(self.path + ".tmp")
            return
        for i in range(self.backups, 0, -1):
            src = self.path if i == 1 else f"{self.path}.{i - 1}"
            if os.path.exists(src):
                os.replace(src, f"{self.path}.{i}")

    def write(self, event: str, **data) -> None:
        rec = {"ts": round(time.time(), 3), "event": event}
        for k, v in data.items():
            rec[k] = safe(v, 2000, False) if isinstance(v, str) else v
        line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        with self._lock:
            try:
                if os.path.exists(self.path) and os.path.getsize(self.path) + len(line) > self.max_bytes:
                    self._rotate()
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                with os.fdopen(fd, "a", encoding="utf-8") as f:
                    f.write(line)
            except OSError:
                pass  # günlük yazılamıyorsa daemon'ı düşürme
